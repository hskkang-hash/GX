from ninja_extra import api_controller, route
from typing import List
from ninja.errors import ValidationError
from common.pagination import OptimizedPaginator

from devices.utils import filter_mensurement
from devices.services.packaging_service import PackagingSpecificationService
from devices.models import PackagingSpecification, Measurement
from devices.schemas.schemas_djantic_in import PackagingSpecificationInSchema
from devices.schemas.schemas_djantic_out import PackagingSpecificationOutSchema
from core.api.v1.auth import CustomJWTAuth
from core.common.base_response import BaseResponse
from core.common.search.dynamic_search import build_dynamic_query_from_queryset, apply_dynamic_filters
from common.constant import MESSAGE_ENUM
from core.role.permission import path_permission
@api_controller('/packaging-specifications', tags=['Packaging Specifications'])
class PackagingSpecificationAPI:
    @route.get('')
    @path_permission("read", "/packaging")
    def list_packaging_specifications(self, request):
        page_size = int(request.GET.get('page_size', 25))
        current_page = int(request.GET.get('current_page', 1))
        
        specifications = PackagingSpecification.objects.select_related('package_type').all().order_by('-id')
        query = filter_mensurement(specifications, PackagingSpecification, request)

 
        query = apply_dynamic_filters(query, request, [], request.GET.get('sort_obj', None))

        
        # 🚀 OPTIMIZED: Use OptimizedPaginator to automatically optimize COUNT query
        paginator = OptimizedPaginator(query, page_size)
        pages = paginator.page(current_page)
        data = PackagingSpecificationService.get_list_specification_data(pages.object_list)
        
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_LIST_PACKAGING_SPECIFICATION_SUCCESS),
            data=data,
            total_pages=paginator.num_pages,
            total_items=paginator.count,
            current_page=current_page
        )

    @route.get('/{id}')
    @path_permission("read", "/packaging")
    def get_packaging_specification(self, id: int, edit: bool=True):
        try:
            specification = PackagingSpecification.objects.get(id=id)
            _, data = PackagingSpecificationService.get_single_specification_data(id,edit)
            # Sử dụng schema như các model khác thay vì service
            return BaseResponse(
                status_code=200,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_PACKAGING_SPECIFICATION_DETAIL_SUCCESS),
                data=data
            )
        except PackagingSpecification.DoesNotExist:
            return BaseResponse(
                status_code=404,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.NOT_FOUND, "Packaging specification"),
                data=None
            )

    @route.post('', auth=CustomJWTAuth())
    @path_permission("create", "/packaging")
    def create_packaging_specification(self, data: PackagingSpecificationInSchema):
        try:
            # Tạo đối tượng PackagingSpecification cơ bản
            specification = PackagingSpecification.objects.create(
                name=data.name,
                code=data.code,
                package_type_id=data.package_type_id,
                water_proof=data.water_proof,
                fragile=data.fragile,
                note=data.note,
            )
            
            # Xử lý measurements sau khi tạo
            if hasattr(data, 'dimensions') and data.dimensions:
                Measurement.create_from_string(specification, 'dimensions', data.dimensions)
            if hasattr(data, 'max_weight') and data.max_weight:
                Measurement.create_from_string(specification, 'max_weight', data.max_weight)
            return BaseResponse(
                status_code=200,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.CREATE_PACKAGING_SPECIFICATION_SUCCESS),
                data=PackagingSpecificationService.get_single_specification_data(specification.id)
            )
                
        except ValidationError as e:
            return {"success": False, "errors": e.errors()}

    @route.put('/{id}', auth=CustomJWTAuth())
    @path_permission("update", "/packaging")
    def update_packaging_specification(self, id: int, data: PackagingSpecificationInSchema):
        try:
            specification = PackagingSpecification.objects.get(id=id)
            # Cập nhật các trường cơ bản
            if hasattr(data, 'name') and data.name:
                specification.name = data.name
            else:
                specification.name = None
            if hasattr(data, 'code') and data.code:
                specification.code = data.code
            else:
                specification.code = None
            if hasattr(data, 'package_type_id') and data.package_type_id:
                specification.package_type_id = data.package_type_id
            else:
                specification.package_type_id = None
            if hasattr(data, 'water_proof') and data.water_proof:
                specification.water_proof = data.water_proof
            else:
                specification.water_proof = None
            if hasattr(data, 'fragile') and data.fragile:
                specification.fragile = data.fragile
            else:
                specification.fragile = False
            if hasattr(data, 'note') and data.note:
                specification.note = data.note
            else:
                specification.note = None
                
            specification.save()
            
            # Xử lý measurements
            if hasattr(data, 'dimensions') and data.dimensions:
                # Xóa measurement cũ nếu có
                specification.measurements.filter(measurement_type='dimensions').delete()
                # Tạo measurement mới
                Measurement.create_from_string(specification, 'dimensions', data.dimensions)
            else:
                specification.measurements.filter(measurement_type='dimensions').delete()
            if hasattr(data, 'max_weight') and data.max_weight:
                specification.measurements.filter(measurement_type='max_weight').delete()
                Measurement.create_from_string(specification, 'max_weight', data.max_weight)
            else:
                specification.measurements.filter(measurement_type='max_weight').delete()
            return BaseResponse(
                status_code=200,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.UPDATE_PACKAGING_SPECIFICATION_SUCCESS),
                data=PackagingSpecificationOutSchema.from_queryset(specification)
            )
                
        except PackagingSpecification.DoesNotExist:
            return BaseResponse(
                status_code=404,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.NOT_FOUND, "Packaging specification"),
                data=None
            )
        except ValidationError as e:
            return {"success": False, "errors": e.errors()}

    @route.delete('/{id}', auth=CustomJWTAuth())
    @path_permission("delete", "/packaging")
    def delete_packaging_specification(self, id: int):
        try:
            specification = PackagingSpecification.objects.get(id=id)
            specification.delete()
            return BaseResponse(
                status_code=200,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DELETE_SUCCESS),
                data=None
            )
        except PackagingSpecification.DoesNotExist:
            return BaseResponse(
                status_code=404,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DELETE_FAILED),
                data=None
            )
        except Exception:
            return BaseResponse(
                status_code=400,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DELETE_FAILED),
                data=None,
            )
        
    @route.put("/{ids}/change-status", auth=CustomJWTAuth())
    @path_permission("update", "/packaging")
    def change_status(self, ids: str):
        try:
            id_list = [int(id.strip()) for id in ids.split(",")]
        except ValueError:
            # Trường hợp không thể chuyển đổi thành số nguyên
            return BaseResponse.with_message(
                success=False,
                status_code=400,
                message="Invalid ID format. Please provide comma-separated integers."
            )
        specifications = PackagingSpecification.objects.filter(id__in=id_list)
        message_key = None
        for specification in specifications:
            specification.active = not specification.active
            specification.save()
            if message_key is None:
                message_key = (
                    MESSAGE_ENUM.ACTION_ACTIVATE_SUCCESS
                    if specification.active
                    else MESSAGE_ENUM.ACTION_DEACTIVATE_SUCCESS
                )
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(message_key or MESSAGE_ENUM.ACTION_ACTIVATE_SUCCESS),
            data=None,
        )
    
    @route.put("/{ids}/activate", auth=CustomJWTAuth())
    @path_permission("update", "/packaging")
    def activate(self, ids: str):
        try:
            id_list = [int(id.strip()) for id in ids.split(",")]
        except ValueError:
            return BaseResponse.with_message(
                success=False,
                status_code=400,
                message="Invalid ID format. Please provide comma-separated integers."
            )
        specifications = PackagingSpecification.objects.filter(id__in=id_list)
        for specification in specifications:
            specification.active = True
            specification.save()
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_ACTIVATE_SUCCESS),
        )
    
    @route.put("/{ids}/deactivate", auth=CustomJWTAuth())
    @path_permission("update", "/packaging")
    def deactivate(self, ids: str):
        try:
            id_list = [int(id.strip()) for id in ids.split(",")]
        except ValueError:
            return BaseResponse.with_message(
                success=False,
                status_code=400,
                message="Invalid ID format. Please provide comma-separated integers."
            )
        specifications = PackagingSpecification.objects.filter(id__in=id_list)
        for specification in specifications:
            specification.active = False
            specification.save()
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DEACTIVATE_SUCCESS),
        )
    
    @route.put("/{ids}/change-active", auth=CustomJWTAuth())
    @path_permission("update", "/packaging")
    def change_active(self, ids: str):
        try:
            id_list = [int(id.strip()) for id in ids.split(",")]
        except ValueError:
            return BaseResponse.with_message(
                success=False,
                status_code=400,
                message="Invalid ID format. Please provide comma-separated integers."
            )
        specifications = PackagingSpecification.objects.filter(id__in=id_list)
        for specification in specifications:
            specification.active = not specification.active
            specification.save()
        return BaseResponse(status_code=200,message=MESSAGE_ENUM.get(MESSAGE_ENUM.UPDATE_PACKAGING_SPECIFICATION_SUCCESS))