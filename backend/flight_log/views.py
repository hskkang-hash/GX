from core.common.search.dynamic_search import apply_dynamic_filters
from ninja_extra import api_controller, route
from common.pagination import OptimizedPaginator
from core.role.permission import path_permission
from core.common.base_response import BaseResponse
from flight_log.schemas.schemas_djantic_out import FlightLogOutSchema
from flight_log.services.flight_log_service import FlightLogService
from terminals.models import Routes
from common.constant import MESSAGE_ENUM
from devices.models import Measurement
from django.contrib.contenttypes.models import ContentType
from django.http import JsonResponse

@api_controller('/flight-log', tags=['Flight Log'])
class FlightLogAPI:
    @route.get('/', url_name='get_flight_log')
    @path_permission("read", path_override='/flight-log-analysis')
    def get_flight_log(self, request):
        try:
            page_size = int(request.GET.get('page_size', 25))
            current_page = int(request.GET.get('current_page', 1))
            
            # Get optimized queryset (no iteration, just builds query)
            flight_log = FlightLogService.get_flight_logs_queryset()

            if request.GET.get('drone_anomaly_prediction__name'):
                drone_anomaly_prediction_filter = request.GET.get('drone_anomaly_prediction__name')
                flight_log = flight_log.filter(drone_anomaly_prediction__name__icontains=drone_anomaly_prediction_filter)
            
            # Apply dynamic filters and sorting
            query = apply_dynamic_filters(flight_log, request, [], request.GET.get('sort_obj'))
            
            # Paginate FIRST - only fetch the records we need
            paginator = OptimizedPaginator(query, page_size)
            pages = paginator.page(current_page)
            
            # Convert to schema - measurements are handled via annotate in queryset
            datas = FlightLogOutSchema.from_queryset(pages.object_list, many=True)
            
            return BaseResponse(
                status_code=200, 
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_LIST_FLIGHT_LOG_SUCCESS), 
                data=datas, 
                total_pages=paginator.num_pages, 
                total_items=paginator.count, 
                current_page=current_page
            )
        except Exception as e:
            return BaseResponse(status_code=500, message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_LIST_FLIGHT_LOG_FAILED), data=[], total_pages=0, total_items=0, current_page=1)


    @route.get('/detail/{id}', url_name='get_flight_log_detail')
    @path_permission("read", path_override='/flight-log-analysis')
    def get_flight_log_detail(self, request, id: int):
        try:
            flight_log = FlightLogService.get_flight_log_detail(id)
            return BaseResponse(status_code=200, message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_FLIGHT_LOG_DETAIL_SUCCESS), data=flight_log)
        except Exception as e:
            return BaseResponse(status_code=500, message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_FLIGHT_LOG_DETAIL_FAILED), data=[])

    @route.get('/download-log/{id}', url_name='download_log_file')
    @path_permission("read", path_override='/flight-log-analysis')
    def download_log_file(self, request, id: int):
        try:
            flight_log_data = FlightLogService.get_flight_log_detail(id)
            
            # Create JSON response with file download headers
            response = JsonResponse(flight_log_data, safe=False, json_dumps_params={'indent': 2, 'ensure_ascii': False})
            response['Content-Disposition'] = f'attachment; filename="flight_log_{id}.json"'
            response['Content-Type'] = 'application/json'
            return response
        except Exception as e:
            return BaseResponse(status_code=500, message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_FLIGHT_LOG_DETAIL_FAILED), data=[])

    @route.delete('/delete/{ids}', url_name='delete_flight_log')
    @path_permission("delete", path_override='/flight-log-analysis')
    def delete_flight_log(self, request, ids: str):
        try:
            success, message = FlightLogService.delete_flight_log(ids)
            if success:
                return BaseResponse(status_code=200, message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DELETE_SUCCESS), data=message)
            else:
                return BaseResponse(status_code=400, message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DELETE_FAILED), data=message)
        except Exception as e:
            return BaseResponse(status_code=500, message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DELETE_FAILED), data=e)