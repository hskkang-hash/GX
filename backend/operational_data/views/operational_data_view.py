from operational_data.schemas.schemas_djantic_out import OperationalDataListOutSchema
from operational_data.schemas.schemas_djantic_in import DownloadOperationalDataInSchema
from operational_data.services.operational_data_service import OperationalDataService
from ninja import File, Query
from ninja_extra import api_controller, route
from ninja.files import UploadedFile
from typing import List, Optional
from common.pagination import OptimizedPaginator
from core.role.permission import path_permission
from core.common.search.dynamic_search import apply_dynamic_filters
from core.common.base_response import BaseResponse
from common.tenant_filters import assert_scoped
from orders.models import OrderItem
from core.api.v1.auth import CustomJWTAuth
from core.user.models import DateFormat, TimeFormat
from common.constant import MESSAGE_ENUM
from datetime import datetime

@api_controller('/operational-data', tags=['Operational Data'])
class OperationalDataAPI:
    @route.get('', auth=CustomJWTAuth())
    @path_permission("read", path_override="/operational-data")
    def get_operational_data(self, delivery_operation_code: str = None, delivered_at: str = None, route: str = None, delivery_point: str = None, item_type_code: str = None, item_weight: str = None):
        try:
            request = self.context.request
            page_size = int(request.GET.get('page_size', 25))
            current_page = int(request.GET.get('current_page', 1))
            language = request.user.language.code if request.user.language else 'en'
            operational_data = OperationalDataService.get_operational_data()
            operational_data = apply_dynamic_filters(operational_data, request, [], request.GET.get('sort_obj'))

            # 🚀 OPTIMIZED: Use OptimizedPaginator to automatically optimize COUNT query
            paginator = OptimizedPaginator(operational_data, page_size)
            pages = paginator.page(current_page)

            data = OperationalDataListOutSchema.from_queryset(pages.object_list, many=True)
            if hasattr(data, '__iter__') and len(data) > 0:
                for i, operational_data in enumerate(pages.object_list):
                    type = operational_data.item_type
                    if type:
                        type = type.get_translation('name', language)
                        data[i]['item_type'] = type
            return BaseResponse(status_code=200,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_LIST_OPERATIONAL_DATA_SUCCESS),
                data = data,
                total_pages=paginator.num_pages,
                total_items=paginator.count,
                current_page=current_page,
            )
        except Exception as e:
            return BaseResponse(status_code=500, message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_LIST_OPERATIONAL_DATA_FAILED))

    @route.get('/download-operational-data')
    # @path_permission("read", path_override="/operational-data")
    def download_operational_data(self, request, order_item_ids: List[int] = Query(...)):
        try:
            result = OperationalDataService.download_operational_data(order_item_ids)
            if result['success']:
                return BaseResponse(
                    status_code=202,  # 202 Accepted for async processing
                    message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_EXPORT_SUCCESS),
                    data={
                        'download_task_id': result['download_task_id'],
                        'download_status_id': result['download_status_id'],
                        'total_order_items': result['total_order_items'],
                        'message': result['message']
                    }
                )
            else:
                return BaseResponse(
                    status_code=400,
                    message=MESSAGE_ENUM.get(MESSAGE_ENUM.OPERATIONAL_DATA_EMPTY),
                    data={'error': result.get('error', 'Unknown error')}
                )
        except Exception as e:
            return BaseResponse(status_code=500, message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_EXPORT_FAILED))

    @route.get('/{order_item_id}')
    @path_permission("read", path_override="/operational-data")
    def get_operational_data_detail(self, request, order_item_id: int):
        # ★ 문지기는 try **밖**이다 (W0-14c). 아래 except 가 모든 예외를 500 으로 덮어
        #   "막힌 것"과 "찾은 뒤 죽은 것"을 구별할 수 없게 만든다.
        #   실측(2026-08-28): 남의 테넌트 pk 에 **500** 이 나갔다 — 매니저가 걸러 누출은
        #   없었으나 그 500 은 답이 아니다. 우연한 차단에 기대지 않는다
        #   (매니저 필터에는 created_by__isnull OR 절이 있어 소유가 빈 행을 못 거른다).
        assert_scoped(OrderItem, order_item_id, request.user)
        try:
            operational_data = OperationalDataService.get_operational_data_detail(order_item_id)
            language = request.user.language.code if request.user.language else 'en'
            data = OperationalDataListOutSchema.from_queryset(operational_data, many=False)
            type = operational_data.item_type
            if type:
                type = type.get_translation('name', language)
                data['item_type'] = type
            return BaseResponse(status_code=200, message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_LIST_OPERATIONAL_DATA_SUCCESS), data=data)
        except Exception as e:
            return BaseResponse(status_code=500, message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_LIST_OPERATIONAL_DATA_FAILED))

    @route.post('/{order_item_id}/upload-operational-log-drone')
    # @path_permission("create", path_override="/operational-data")
    def upload_operational_log_drone(self, request, order_item_id: int, files: List[UploadedFile] = File(None)):
        try:
            result = OperationalDataService.upload_operational_log_drone(order_item_id, files)
            if result['success']:
                return BaseResponse(
                    status_code=202,  # 202 Accepted for async processing
                    message=MESSAGE_ENUM.get(MESSAGE_ENUM.UPLOAD_OPERATIONAL_LOG_DRONE_SUCCESS),
                    data={
                        'task_id': result['task_id'],
                        'upload_status_id': result['upload_status_id'],
                        'total_files': result['total_files'],
                        'queue_position': result.get('queue_position'),
                        'message': result['message']
                    }
                )
            else:
                return BaseResponse(
                    status_code=400,
                    message=MESSAGE_ENUM.get(MESSAGE_ENUM.UPLOAD_OPERATIONAL_LOG_DRONE_FAILED),
                    data={'error': result.get('error', 'Unknown error')}
                )
        except Exception as e:
            return BaseResponse(status_code=500, message=MESSAGE_ENUM.get(MESSAGE_ENUM.UPLOAD_OPERATIONAL_LOG_DRONE_FAILED))

    @route.post('/{order_item_id}/upload-operational-log-robot')
    # @path_permission("create", path_override="/operational-data")
    def upload_operational_log_robot(self, request, order_item_id: int, files: List[UploadedFile] = File(None)):
        try:
            result = OperationalDataService.upload_operational_log_robot(order_item_id, files)
            if result['success']:
                return BaseResponse(
                    status_code=202,  # 202 Accepted for async processing
                    message=MESSAGE_ENUM.get(MESSAGE_ENUM.UPLOAD_OPERATIONAL_LOG_ROBOT_SUCCESS),
                    data={
                        'task_id': result['task_id'],
                        'upload_status_id': result['upload_status_id'],
                        'total_files': result['total_files'],
                        'queue_position': result.get('queue_position'),
                        'message': result['message']
                    }
                )
            else:
                return BaseResponse(
                    status_code=400,
                    message=MESSAGE_ENUM.get(MESSAGE_ENUM.UPLOAD_OPERATIONAL_LOG_ROBOT_FAILED),
                    data={'error': result.get('error', 'Unknown error')}
                )
        except Exception as e:
            return BaseResponse(status_code=500, message=MESSAGE_ENUM.get(MESSAGE_ENUM.UPLOAD_OPERATIONAL_LOG_ROBOT_FAILED))

    @route.post('/{order_item_id}/upload-operational-video-drone')
    # @path_permission("create", path_override="/operational-data")
    def upload_operational_video_drone(self, request, order_item_id: int, files: List[UploadedFile] = File(None)):
        try:
            result = OperationalDataService.upload_operational_video_drone(order_item_id, files)
            if result['success']:
                return BaseResponse(
                    status_code=202,  # 202 Accepted for async processing
                    message=MESSAGE_ENUM.get(MESSAGE_ENUM.UPLOAD_OPERATIONAL_VIDEO_DRONE_SUCCESS),
                    data={
                        'task_id': result['task_id'],
                        'upload_status_id': result['upload_status_id'],
                        'total_files': result['total_files'],
                        'queue_position': result.get('queue_position'),
                        'message': result['message']
                    }
                )
            else:
                return BaseResponse(
                    status_code=400,
                    message=MESSAGE_ENUM.get(MESSAGE_ENUM.UPLOAD_OPERATIONAL_VIDEO_DRONE_FAILED),
                    data={'error': result.get('error', 'Unknown error')}
                )
        except Exception as e:
            return BaseResponse(status_code=500, message=MESSAGE_ENUM.get(MESSAGE_ENUM.UPLOAD_OPERATIONAL_VIDEO_DRONE_FAILED))

    @route.post('/{order_item_id}/upload-operational-video-robot')
    # @path_permission("create", path_override="/operational-data")
    def upload_operational_video_robot(self, request, order_item_id: int, files: List[UploadedFile] = File(None)):
        try:
            result = OperationalDataService.upload_operational_video_robot(order_item_id, files)
            if result['success']:
                return BaseResponse(
                    status_code=202,  # 202 Accepted for async processing
                    message=MESSAGE_ENUM.get(MESSAGE_ENUM.UPLOAD_OPERATIONAL_VIDEO_ROBOT_SUCCESS),
                    data={
                        'task_id': result['task_id'],
                        'upload_status_id': result['upload_status_id'],
                        'total_files': result['total_files'],
                        'queue_position': result.get('queue_position'),
                        'message': result['message']
                    }
                )
            else:
                return BaseResponse(
                    status_code=400,
                    message=MESSAGE_ENUM.get(MESSAGE_ENUM.UPLOAD_OPERATIONAL_VIDEO_ROBOT_FAILED),
                    data={'error': result.get('error', 'Unknown error')}
                )
        except Exception as e:
            return BaseResponse(status_code=500, message=MESSAGE_ENUM.get(MESSAGE_ENUM.UPLOAD_OPERATIONAL_VIDEO_ROBOT_FAILED))

    @route.get('/{order_item_id}/download-operational-log-drone')
    # @path_permission("read", path_override="/operational-data")
    def download_operational_log_drone(self, request, order_item_id: int):
        try:
            result = OperationalDataService.download_operational_log(order_item_id, 'drone')
            if result['success']:
                return BaseResponse(
                    status_code=202,  # 202 Accepted for async processing
                    message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_EXPORT_SUCCESS),
                    data={
                        'download_task_id': result['download_task_id'],
                        'download_status_id': result['download_status_id'],
                        'device_type': result['device_type'],
                        'order_item_id': result['order_item_id'],
                        'message': result['message']
                    }
                )
            else:
                return BaseResponse(
                    status_code=400,
                    message=MESSAGE_ENUM.get(MESSAGE_ENUM.OPERATIONAL_LOG_DRONE_EMPTY),
                    data={'error': result.get('error', 'Unknown error')}
                )
        except Exception as e:
            return BaseResponse(status_code=500, message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_EXPORT_FAILED))

    @route.get('/{order_item_id}/download-operational-log-robot')
    # @path_permission("read", path_override="/operational-data")
    def download_operational_log_robot(self, request, order_item_id: int):
        try:
            result = OperationalDataService.download_operational_log(order_item_id, 'robot')
            if result['success']:
                return BaseResponse(
                    status_code=202,  # 202 Accepted for async processing
                    message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_EXPORT_SUCCESS),
                    data={
                        'download_task_id': result['download_task_id'],
                        'download_status_id': result['download_status_id'],
                        'device_type': result['device_type'],
                        'order_item_id': result['order_item_id'],
                        'message': result['message'],
                    }
                )
            else:
                return BaseResponse(
                    status_code=400,
                    message=MESSAGE_ENUM.get(MESSAGE_ENUM.OPERATIONAL_LOG_ROBOT_EMPTY),
                    data={'error': result.get('error', 'Unknown error')}
                )
        except Exception as e:
            return BaseResponse(status_code=500, message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_EXPORT_FAILED))

    @route.get('/upload-status/{task_id}', auth=CustomJWTAuth())
    # @path_permission("read", path_override="/operational-data")
    def get_upload_status_by_task_id(self, request, task_id: str):
        try:
            result = OperationalDataService.get_upload_status(task_id=task_id)
            if result['success']:
                return BaseResponse(
                    status_code=200,
                    message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_LIST_OPERATIONAL_DATA_SUCCESS),
                    data=result['data']
                )
            else:
                return BaseResponse(
                    status_code=404,
                    message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_LIST_OPERATIONAL_DATA_FAILED),
                    data={'error': result.get('error', 'Upload status not found')}
                )
        except Exception as e:
            return BaseResponse(status_code=500, message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_LIST_OPERATIONAL_DATA_FAILED))

    @route.get('/upload-status/id/{upload_status_id}', auth=CustomJWTAuth())
    # @path_permission("read", path_override="/operational-data")
    def get_upload_status_by_id(self, request, upload_status_id: int):
        try:
            result = OperationalDataService.get_upload_status(upload_status_id=upload_status_id)
            if result['success']:
                return BaseResponse(
                    status_code=200,
                    message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_LIST_OPERATIONAL_DATA_SUCCESS),
                    data=result['data']
                )
            else:
                return BaseResponse(
                    status_code=404,
                    message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_LIST_OPERATIONAL_DATA_FAILED),
                    data={'error': result.get('error', 'Upload status not found')}
                )
        except Exception as e:
            return BaseResponse(status_code=500, message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_LIST_OPERATIONAL_DATA_FAILED))
