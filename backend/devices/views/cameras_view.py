from ninja_extra import api_controller, route
from ninja.errors import ValidationError
from typing import List, Optional

from django.db import transaction
from django.db.models import Q, F
from django.shortcuts import get_object_or_404

from devices.utils import filter_mensurement
from devices.services.camera_service import CameraService
from common.constant import MESSAGE_ENUM
from devices.models import CameraType, Device, Measurement
from devices.schemas.schemas_djantic_in import CameraInSchema
from devices.schemas.schemas_djantic_out import CameraOutSchema
from core.common.base_response import BaseResponse
from core.api.v1.auth import CustomJWTAuth
from common.pagination import OptimizedPaginator
from core.role.permission import path_permission

from core.common.search.dynamic_search import build_dynamic_query_from_queryset, apply_dynamic_filters

@api_controller('/cameras', tags=['Cameras'])
class CameraAPI:
    
    @transaction.atomic
    @route.post("", auth=CustomJWTAuth())
    @path_permission("create", "/other-equipments")
    def create_camera(self, request, data: CameraInSchema):
        # """Tạo mới camera"""
        try:
            # Kiểm tra device nếu được cung cấp
            device = None
            if hasattr(data, 'device_id') and data.device_id:
                device = get_object_or_404(Device, id=data.device_id)
            
            # Tạo camera
            camera = CameraType.objects.create(
                name=data.name,
                image_stabilization_id=data.image_stabilization_id,
                night_vision=data.night_vision,
                thermal_imaging=data.thermal_imaging,
                status=data.status or 'active',
                active=True,
                note=data.note
            )
            
            # Xử lý các trường measurement
            if hasattr(data, 'resolution') and data.resolution:
                Measurement.create_from_string(camera, 'resolution', data.resolution)
            
            if hasattr(data, 'field_of_view') and data.field_of_view:
                Measurement.create_from_string(camera, 'field_of_view', data.field_of_view)
                
            if hasattr(data, 'frame_rate') and data.frame_rate:
                Measurement.create_from_string(camera, 'frame_rate', data.frame_rate)
                
            if hasattr(data, 'weight') and data.weight:
                Measurement.create_from_string(camera, 'weight', data.weight)
                
            if hasattr(data, 'zoom_capability') and data.zoom_capability:
                Measurement.create_from_string(camera, 'zoom_capability', data.zoom_capability)
            
            return BaseResponse(
                status_code=201,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.CREATE_CAMERA_SUCCESS),
                data=CameraOutSchema.from_queryset(camera)
            )
            
        except ValidationError as e:
            return BaseResponse(
                status_code=400,
                message=str(e),
                data=None
            )
            
    @route.get("", auth=CustomJWTAuth())
    @path_permission("read", "/other-equipments")
    def list_cameras(self, request, page_size: int = 25, current_page: int = 1, resolution: str = None, frame_rate: str = None, field_of_view: str = None, weight: str = None, image_stabilization: str = None, night_vision: bool = None, thermal_imaging: bool = None):
        """Lấy danh sách cameras với phân trang và tìm kiếm"""
        # Base queryset

        queryset = CameraType.objects.all().order_by('-id').annotate(image_stabilization__name=F('image_stabilization__name'))
        query = filter_mensurement(queryset, CameraType, request)

        query = apply_dynamic_filters(query, request, [], request.GET.get('sort_obj', None))

        # 🚀 OPTIMIZED: Use OptimizedPaginator to automatically optimize COUNT query
        paginator = OptimizedPaginator(query, page_size)
        cameras = paginator.page(current_page)
        data = CameraOutSchema.from_queryset(cameras.object_list, many=True)

        # Return response
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_LIST_CAMERA_SUCCESS),
            data=data,
            total_pages=paginator.num_pages,
            total_items=paginator.count,
            current_page=current_page
        )
        
    @route.get("/{id}", auth=CustomJWTAuth())
    @path_permission("read", "/other-equipments")
    def get_camera(self, request, id: int, edit: bool=True):
        """Lấy thông tin chi tiết một camera"""
        try:
            camera = get_object_or_404(CameraType, id=id)
            data = CameraService.get_data(camera, edit=edit)
            return BaseResponse(
                status_code=200,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_CAMERA_DETAIL_SUCCESS),
                data=data
            )
        except:
            return BaseResponse(
                status_code=404,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_CAMERA_DETAIL_FAILED),
                data=None
            )
            
    @transaction.atomic
    @route.put("/{id}", auth=CustomJWTAuth())
    @path_permission("update", "/other-equipments")
    def update_camera(self, request, id: int, data: CameraInSchema):
        """Cập nhật thông tin camera"""
        try:
            camera = get_object_or_404(CameraType, id=id)
            
            # Cập nhật các trường cơ bản
            camera.name = data.name
            camera.status = data.status
            
            # Cập nhật các trường tùy chọn
            if hasattr(data, 'image_stabilization_id') and data.image_stabilization_id is not None:
                camera.image_stabilization_id = data.image_stabilization_id
            else:
                camera.image_stabilization_id = None
            if hasattr(data, 'night_vision') and data.night_vision is not None:
                camera.night_vision = data.night_vision
            else:
                camera.night_vision = False
            if hasattr(data, 'thermal_imaging') and data.thermal_imaging is not None:
                camera.thermal_imaging = data.thermal_imaging
            else:
                camera.thermal_imaging = False
            
            if hasattr(data, 'note') and data.note is not None:
                camera.note = data.note
            else:
                camera.note = None
            # Cập nhật device nếu được cung cấp
            if hasattr(data, 'device_id') and data.device_id:
                device = get_object_or_404(Device, id=data.device_id)
                camera.device = device
            
            camera.save()
            
            # Xử lý các trường measurement
            if hasattr(data, 'resolution') and data.resolution:
                camera.measurements.filter(measurement_type='resolution').delete()
                Measurement.create_from_string(camera, 'resolution', data.resolution)
            else:
                camera.measurements.filter(measurement_type='resolution').delete()
            if hasattr(data, 'field_of_view') and data.field_of_view:
                camera.measurements.filter(measurement_type='field_of_view').delete()
                Measurement.create_from_string(camera, 'field_of_view', data.field_of_view)
            else:
                camera.measurements.filter(measurement_type='field_of_view').delete()
            if hasattr(data, 'frame_rate') and data.frame_rate:
                camera.measurements.filter(measurement_type='frame_rate').delete()
                Measurement.create_from_string(camera, 'frame_rate', data.frame_rate)
            else:
                camera.measurements.filter(measurement_type='frame_rate').delete()
            if hasattr(data, 'weight') and data.weight:
                camera.measurements.filter(measurement_type='weight').delete()
                Measurement.create_from_string(camera, 'weight', data.weight)
            else:
                camera.measurements.filter(measurement_type='weight').delete()
            if hasattr(data, 'zoom_capability') and data.zoom_capability:
                camera.measurements.filter(measurement_type='zoom_capability').delete()
                Measurement.create_from_string(camera, 'zoom_capability', data.zoom_capability)
            else:
                camera.measurements.filter(measurement_type='zoom_capability').delete()
            return BaseResponse(
                status_code=200,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.UPDATE_CAMERA_SUCCESS),
                data=CameraOutSchema.from_queryset(camera)
            )
        except ValidationError as e:
            return BaseResponse(
                status_code=400,
                message=str(e),
                data=None
            )
            
    @transaction.atomic
    @route.delete("/{id}", auth=CustomJWTAuth())
    @path_permission("delete", "/other-equipments")
    def delete_camera(self, request, id: int):
        """Xóa camera"""
        try:
            camera = get_object_or_404(CameraType, id=id)
            
            # Xóa các measurement liên quan
            camera.clear_measurements()
            
            # Xóa camera
            camera.delete()
            
            return BaseResponse(
                status_code=200,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DELETE_SUCCESS),
                data=None
            )
        except:
            return BaseResponse(
                status_code=404,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DELETE_FAILED),
                data=None
            )
            
    @route.get("/device/{device_id}", auth=CustomJWTAuth())
    @path_permission("read", "/other-equipments")
    def get_device_cameras(self, request, device_id: int):
        """Lấy danh sách cameras của một thiết bị cụ thể"""
        try:
            device = get_object_or_404(Device, id=device_id)
            cameras = CameraType.objects.filter(device=device)
            
            return BaseResponse(
                status_code=200,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_DEVICE_CAMERAS_SUCCESS),
                data=CameraOutSchema.from_queryset(cameras)
            )
        except:
            return BaseResponse(
                status_code=404,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_DEVICE_CAMERAS_FAILED),
                data=None
            )

    @route.put("/{id}/change-status", auth=CustomJWTAuth())
    @path_permission("update", "/other-equipments")
    def change_status(self, request, id: str):
        """Thay đổi trạng thái của camera"""
        try:
            ids = id.split(",")
            for camera_id in ids:
                camera = get_object_or_404(CameraType, id=camera_id)
                camera.active = not camera.active
                camera.save()
            return BaseResponse(
                status_code=200,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.UPDATE_CAMERA_SUCCESS),
                data=None
            )
        except:
            return BaseResponse(
                status_code=404,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.UPDATE_CAMERA_FAILED),
                data=None
            )
        
    @route.put("/{id}/activate", auth=CustomJWTAuth())
    @path_permission("update", "/other-equipments")
    def activate(self, request, id: str):
        """Thay đổi trạng thái của camera"""
        try:
            ids = id.split(",")
            for camera_id in ids:
                camera = get_object_or_404(CameraType, id=camera_id)
                camera.active = True
                camera.save()
            return BaseResponse(
                status_code=200,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_ACTIVATE_SUCCESS),
                data=None
            )
        except:
            return BaseResponse(
                status_code=404,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_ACTIVATE_FAILED),
                data=None
            )

    @route.put("/{id}/deactivate", auth=CustomJWTAuth())
    @path_permission("update", "/other-equipments")
    def deactivate(self, request, id: str):
        """Thay đổi trạng thái của camera"""
        try:
            ids = id.split(",")
            for camera_id in ids:
                camera = get_object_or_404(CameraType, id=camera_id)
                camera.active = False
                camera.save()     
            return BaseResponse(
                status_code=200,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DEACTIVATE_SUCCESS),
                data=None
            )
        except:
            return BaseResponse(
                status_code=404,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DEACTIVATE_FAILED),
                data=None
            )