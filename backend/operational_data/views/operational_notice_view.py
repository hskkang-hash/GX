from ninja_extra import api_controller, route
from operational_data.schemas.schemas_djantic_in import OperationalNoticeCreateInSchema, OperationalNoticeUpdateInSchema, OperationalNoticeBulkDeleteInSchema
from operational_data.schemas.schemas_djantic_out import OperationalNoticeOutSchema
from operational_data.services.operational_notice_service import OperationalNoticeService
from core.common.base_response import BaseResponse
from core.api.v1.auth import CustomJWTAuth
from core.role.permission import path_permission
from common.constant import MESSAGE_ENUM
from typing import List
from common.pagination import OptimizedPaginator
from core.common.search.dynamic_search import apply_dynamic_filters

@api_controller('/operational-notice', tags=['Operational Notice'])
class OperationalNoticeAPI:
    """API endpoints cho OperationalNotice CRUD operations"""
    
    @route.get('', auth=CustomJWTAuth())
    @path_permission("read", path_override="/operational-notice")
    def get_operational_notice_list(self, request):
        """Lấy danh sách tất cả operational notices"""
        try:
            page_size = int(request.GET.get('page_size', 25))
            current_page = int(request.GET.get('current_page', 1))
            success, result = OperationalNoticeService.get_operational_notice_list()
            result['data'] = apply_dynamic_filters(result['data'], request, [], request.GET.get('sort_obj'))
            # 🚀 OPTIMIZED: Use OptimizedPaginator to automatically optimize COUNT query
            paginator = OptimizedPaginator(result['data'], page_size)
            pages = paginator.page(current_page)
            data = OperationalNoticeOutSchema.from_queryset(pages.object_list, many=True)
            if success:
                return BaseResponse(
                    status_code=200,
                    message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_LIST_SUCCESS),
                    data=data,
                    total_pages=paginator.num_pages,
                    total_items=paginator.count,
                    current_page=current_page
                )
            else:
                return BaseResponse(
                    status_code=500,
                    message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_LIST_FAILED),
                    data={'error': result.get('error')}
                )
                
        except Exception as e:
            print(e)
            return BaseResponse(
                status_code=500,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_LIST_FAILED)
            )
    
    @route.get('/{notice_id}', auth=CustomJWTAuth())
    @path_permission("read", path_override="/operational-notice")
    def get_operational_notice_detail(self, notice_id: int):
        """Lấy chi tiết một operational notice"""
        try:
            success, result = OperationalNoticeService.get_operational_notice_detail(notice_id)
            
            if success:
                return BaseResponse(
                    status_code=200,
                    message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_SUCCESS),
                    data=result['data']
                )
            else:
                if result.get('error') == 'Not found':
                    return BaseResponse(
                        status_code=404,
                        message=MESSAGE_ENUM.get(MESSAGE_ENUM.NOT_FOUND),
                        data={'error': result.get('error')}
                    )
                else:
                    return BaseResponse(
                        status_code=500,
                        message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_FAILED),
                        data={'error': result.get('error')}
                    )
                
        except Exception as e:
            return BaseResponse(
                status_code=500,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_FAILED)
            )
    
    @route.post('', auth=CustomJWTAuth())
    @path_permission("create", path_override="/operational-notice")
    def create_operational_notice(self, data: OperationalNoticeCreateInSchema):
        """Tạo mới operational notice"""
        try:
            success, result = OperationalNoticeService.create_operational_notice(data)
            
            if success:
                return BaseResponse(
                    status_code=201,
                    message=MESSAGE_ENUM.get(MESSAGE_ENUM.CREATE_SUCCESS),
                    data=result['data']
                )
            else:
                if result.get('error') == 'Validation error':
                    return BaseResponse(
                        status_code=400,
                        message=MESSAGE_ENUM.get(MESSAGE_ENUM.VALIDATION_ERROR),
                        data={'error': result.get('error'), 'details': result.get('details')}
                    )
                else:
                    return BaseResponse(
                        status_code=500,
                        message=MESSAGE_ENUM.get(MESSAGE_ENUM.CREATE_FAILED),
                        data={'error': result.get('error')}
                    )
                
        except Exception as e:
            return BaseResponse(
                status_code=500,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.CREATE_FAILED)
            )
    
    @route.put('/{notice_id}', auth=CustomJWTAuth())
    @path_permission("update", path_override="/operational-notice")
    def update_operational_notice(self, notice_id: int, data: OperationalNoticeUpdateInSchema):
        """Cập nhật operational notice"""
        try:
            success, result = OperationalNoticeService.update_operational_notice(notice_id, data)
            
            if success:
                return BaseResponse(
                    status_code=200,
                    message=MESSAGE_ENUM.get(MESSAGE_ENUM.UPDATE_SUCCESS),
                    data=result['data']
                )
            else:
                if result.get('error') == 'Not found':
                    return BaseResponse(
                        status_code=404,
                        message=MESSAGE_ENUM.get(MESSAGE_ENUM.NOT_FOUND),
                        data={'error': result.get('error')}
                    )
                elif result.get('error') == 'Validation error':
                    return BaseResponse(
                        status_code=400,
                        message=MESSAGE_ENUM.get(MESSAGE_ENUM.VALIDATION_ERROR),
                        data={'error': result.get('error'), 'details': result.get('details')}
                    )
                else:
                    return BaseResponse(
                        status_code=500,
                        message=MESSAGE_ENUM.get(MESSAGE_ENUM.UPDATE_FAILED),
                        data={'error': result.get('error')}
                    )
                
        except Exception as e:
            return BaseResponse(
                status_code=500,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.UPDATE_FAILED)
            )
    
    @route.delete('delete/{notice_ids}', auth=CustomJWTAuth())
    @path_permission("delete", path_override="/operational-notice")
    def delete_operational_notice(self, notice_ids: str):
        """Xóa operational notice"""
        try:
            success, result = OperationalNoticeService.delete_operational_notice(notice_ids)
            
            if success:
                return BaseResponse(
                    status_code=200,
                    message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DELETE_SUCCESS),
                    data={'message': result}
                )
            else:
                if result.get('error') == 'Not found':
                    return BaseResponse(
                        status_code=404,
                        message=MESSAGE_ENUM.get(MESSAGE_ENUM.NOT_FOUND),
                        data={'error': result.get('error')}
                    )
                else:
                    return BaseResponse(
                        status_code=500,
                        message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DELETE_FAILED),
                        data={'error': result.get('error')}
                    )
                
        except Exception as e:
            return BaseResponse(
                status_code=500,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DELETE_FAILED)
            )
    
    @route.post('/change-status/{notice_id}', auth=CustomJWTAuth())
    @path_permission("update", path_override="/operational-notice")
    def change_status_operational_notice(self, notice_id: int):
        """Thay đổi trạng thái operational notice"""
        try:
            success, message, notice_id = OperationalNoticeService.change_status_operational_notice(notice_id)
            
            if success:
                return BaseResponse(
                    status_code=200,
                    message=MESSAGE_ENUM.get(MESSAGE_ENUM.UPDATE_SUCCESS),
                    data={'message': message, 'notice_id': notice_id}
                )
            else:
                return BaseResponse(
                    status_code=500,
                    message=MESSAGE_ENUM.get(MESSAGE_ENUM.UPDATE_FAILED),
                    data={'error': message}
                )
        except Exception as e:
            return BaseResponse(
                status_code=500,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.UPDATE_FAILED),
                data={'error': str(e)}
            )