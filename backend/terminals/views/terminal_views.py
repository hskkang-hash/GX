import json
from ninja_extra import api_controller, route
from typing import List
from ninja.errors import ValidationError
from common.pagination import OptimizedPaginator

from devices.utils import filter_mensurement, sort_terminal_by_location
from terminals.models import Terminal, TerminalType
from terminals.schemas.schemas_djantic_in import TerminalCreateSchema, TerminalUpdateSchema, TerminalTypeInSchema, FunctionInSchema, TerminalDeactivateSchema
from terminals.schemas.schemas_djantic_out import FunctionTypeOutSchema, LocationTypeOutSchema, TerminalOutSchema, TerminalTypeOutSchema, FunctionOutSchema, TerminalOperatingTimeOutSchema, TerminalExceptionOutSchema
from terminals.services import location_type_service, terminal_service, terminal_type_service, delivery_hub_service, function_service, operating_time_service, exception_service
from core.api.v1.auth import CustomJWTAuth
from core.common.base_response import BaseResponse
from core.common.search.dynamic_search import build_dynamic_query_from_queryset, apply_dynamic_filters
from common.constant import MESSAGE_ENUM
from core.role.permission import path_permission
from core.middleware.refresh_token import get_current_request
from ninja.files import UploadedFile
from typing import List, Optional, Dict, Any
from ninja import Schema, Path, Query, Form, File, Body

@api_controller('/terminals', tags=['Terminals'])
class TerminalsController:
    @route.get('')
    @path_permission("read", path_override='/terminals')
    def list_terminals(
        self, 
        request,
        recipient_city_province: str = None,
        recipient_city_county_district: str = None,
        recipient_ward_town_township: str = None,
        recipient_street_address: str = None,
        route_required: bool = None,
        is_active: bool = None,
        page_size: int = 25,
        current_page: int = 1,
        time_stops: str = None
    ):
        """
        Get paginated list of regular terminals with optional filtering and sorting,
        excluding docking stations and infrastructure terminals
         
        Parameters:
        - page_size: Number of items per page
        - current_page: Current page number
        - sort_obj: JSON string for sorting (e.g. {"field": "created_on", "order": "desc"})
        - recipient_city_province: Filter by recipient's city/province
        - recipient_city_county_district: Filter by recipient's county/district
        - recipient_ward_town_township: Filter by recipient's ward/town/township
        - recipient_street_address: Filter by recipient's street address
        """
        page_size = int(request.GET.get('page_size', 25))
        current_page = int(request.GET.get('current_page', 1))
        
        if route_required:
            terminals = terminal_service.get_terminals_by_route()
        else:
            terminals = terminal_service.get_regular_terminals() 

        # terminals = sort_terminal_by_location(terminals, recipient_city_province, recipient_city_county_district, recipient_ward_town_township, recipient_street_address)
        
        query = filter_mensurement(terminals, Terminal, request)
        query = apply_dynamic_filters(query, request, [], request.GET.get('sort_obj'))
        
        # 🚀 OPTIMIZED: Use OptimizedPaginator to automatically optimize COUNT query
        paginator = OptimizedPaginator(query, page_size)
        pages = paginator.page(current_page)
        
        queryset_for_schema = pages.object_list
        
        t = TerminalOutSchema.from_queryset(
            queryset_for_schema,
            many=True,
        )
        
        response = BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_LIST_TERMINAL_SUCCESS),
            data=t,
            total_pages=paginator.num_pages,
            total_items=paginator.count,
            current_page=current_page
        )
        
        return response

    @route.get('/{id}')
    @path_permission("read", path_override='/terminals')
    def get_terminal(self, id: int):
        terminal = terminal_service.get_terminal(id)
        if not terminal:
            return BaseResponse(
                status_code=404,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.NOT_FOUND, "Terminal"),
                data=None
            )

        operating_times = operating_time_service.get_by_terminal(id)
        exceptions = exception_service.get_by_terminal(id)
        t = TerminalOutSchema.from_queryset(terminal, many=False, raw_measurements=True)
        operating = []
        for item in operating_times:
            operating.append(TerminalOperatingTimeOutSchema.from_queryset(item, many=False, auto_resolve_fields=False))
        exceptions_times = []
        for item in exceptions:
            exceptions_times.append(TerminalExceptionOutSchema.from_queryset(item, many=False, auto_resolve_fields=False))
        t['operating_times'] = operating
        t['exceptions'] = exceptions_times
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_TERMINAL_DETAIL_SUCCESS),
            data=t
        )
    @route.get('/{id}/operating-times')
    @path_permission("read", path_override=['/terminals', '/delivery-hubs', '/infrastructure', '/docking-stations'])
    def get_terminal_operating_times(self, id: int):
        """Lấy chi tiết operating times của một terminal"""
        try:
            terminal = Terminal.objects.filter(id=id)
        except Terminal.DoesNotExist:
            return BaseResponse(
                status_code=404,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.NOT_FOUND, "Terminal"),
                data=None
            )
        
        operating_times = operating_time_service.get_by_terminal(id)
        exceptions = exception_service.get_by_terminal(id)
        operating = []
        for item in operating_times:
            operating.append(TerminalOperatingTimeOutSchema.from_queryset(item, many=False, auto_resolve_fields=False))
        exceptions_times = []
        for item in exceptions:
            exceptions_times.append(TerminalExceptionOutSchema.from_queryset(item, many=False, auto_resolve_fields=False))
        data = {
            "operating_times": operating,
            "exceptions": exceptions_times
        }
        
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_LIST_OPERATING_TIME_SUCCESS),
            data=data
        )

    @route.post('', auth=CustomJWTAuth())
    @path_permission("create", path_override='/terminals')
    def create_terminal(self, request, data: str = Form(..., description="JSON string của TerminalCreateSchema"), avatar: Optional[UploadedFile] = File(None)):
        try:
            data_dict = json.loads(data)
            schema = TerminalCreateSchema(**data_dict)  
            validated_data = schema.dict(exclude_unset=True)
        except Exception as e:
            return BaseResponse(
                status_code=422,
                message=str(e),
                data=None
            )
        if Terminal.objects.filter(code=validated_data.get('code')).exists():
            return BaseResponse(
                status_code=400,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.TERMINAL_CODE_ALREADY_EXISTS),
                data=None
            )
        success, result = terminal_service.create_terminal(validated_data, avatar, request)
        if not success:
            return BaseResponse(
                status_code=400,
                message=str(result),
                data=None
            )
            
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.CREATE_TERMINAL_SUCCESS),
            data=TerminalOutSchema.from_queryset(result)
        )

    @route.put('/{id}', auth=CustomJWTAuth())
    @path_permission("update", path_override='/terminals')
    def update_terminal(self, id: int, request, data: str = Form(..., description="JSON string của TerminalUpdateSchema"), 
                       avatar: Optional[UploadedFile] = File(None)):
        try:
            data_dict = json.loads(data)
            schema = TerminalUpdateSchema(**data_dict)  
            validated_data = schema.dict(exclude_unset=True)
        except Exception as e:
            return BaseResponse(
                status_code=422,
                message=str(e),
                data=None
            )
        if Terminal.objects.filter(code=validated_data.get('code')).exclude(id=id).exists():
            return BaseResponse(
                status_code=400,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.TERMINAL_CODE_ALREADY_EXISTS),
                data=None
            )
        success, result = terminal_service.update_terminal(id, validated_data, avatar, request)
        if not success:
            return BaseResponse(
                status_code=400,
                message=str(result),
                data=None
            )
            
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.UPDATE_TERMINAL_SUCCESS),
            data=TerminalOutSchema.from_queryset(result)
        )

    @route.delete('delete/{ids}', auth=CustomJWTAuth())
    @path_permission("delete", path_override='/terminals')
    def delete_terminal(self, ids: str):
        success, result = terminal_service.delete_terminals(ids)
        if not success:
            return BaseResponse(
                status_code=400,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DELETE_FAILED),
                data=None
            )
            
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DELETE_SUCCESS),
            data=None
        )
    
    @route.put('/{ids}/activate', auth=CustomJWTAuth())
    @path_permission("update", path_override='/terminals')
    def activate(self, ids: str):
        success, result = terminal_service.activate(ids)
        if not success:
            return BaseResponse(
                status_code=400,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_ACTIVATE_FAILED),
                data=None
            )
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_ACTIVATE_SUCCESS),
        )
    
    @route.put('/{ids}/deactivate', auth=CustomJWTAuth())
    @path_permission("update", path_override='/terminals')
    def deactivate(self, ids: str, data: TerminalDeactivateSchema = Body(None)):
        deactivate_reason_id = data.deactivate_reason_id if data else None
        success, result = terminal_service.deactivate(ids, deactivate_reason_id)
        if not success:
            return BaseResponse(
                status_code=400,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DEACTIVATE_FAILED),
                data=None
            )
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DEACTIVATE_SUCCESS),
        )


@api_controller('/docking-stations', tags=['Terminals'])
class DockingStationController:
    @route.get('')
    @path_permission("read", path_override='/docking-stations')
    def list_docking_stations(
        self, 
        request,
        recipient_city_province: str = None,
        recipient_city_county_district: str = None,
        recipient_ward_town_township: str = None,
        recipient_street_address: str = None,
        is_active: bool = None,
        page_size: int = 25,
        current_page: int = 1
    ):
        """
        Get paginated list of docking station terminals with optional filtering and sorting
        
        Parameters:
        - page_size: Number of items per page
        - current_page: Current page number
        - sort_obj: JSON string for sorting (e.g. {"field": "created_on", "order": "desc"})
        """
        page_size = int(request.GET.get('page_size', 25))
        current_page = int(request.GET.get('current_page', 1))
        search_route = request.GET.get('search_route', False)
        terminals = terminal_service.get_docking_station_terminals(search_route=search_route)
                
        query = filter_mensurement(terminals, Terminal, request)
        query = apply_dynamic_filters(query, request, [], request.GET.get('sort_obj'))
        # 🚀 OPTIMIZED: Use OptimizedPaginator to automatically optimize COUNT query
        paginator = OptimizedPaginator(query, page_size)
        pages = paginator.page(current_page)
        # data = []
        # for terminal in pages.object_list:
        #     measurement = terminal.measurements.filter(measurement_type='time_stops').first()
        #     t = TerminalOutSchema.from_queryset(terminal)
        #     if measurement:
        #         t['time_stops'] = measurement.get_formatted_value(None)
        #     else:
        #         t['time_stops'] = None

        #     data.append(t)
     
        # OPTIMIZATION: Sử dụng MeasurableDynamicSchema với bulk measurement loading
        data = TerminalOutSchema.from_queryset(
            pages.object_list, 
            many=True, 
        )
        
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_LIST_TERMINAL_SUCCESS),
            data=data,
            total_pages=paginator.num_pages,
            total_items=paginator.count,
            current_page=current_page
        )
        
    @route.get('/{id}')
    @path_permission("read", path_override='/docking-stations')
    def get_docking_station(self, id: int):
        terminal = terminal_service.get_terminal(id)
        
        if not terminal:
            return BaseResponse(
                status_code=404,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.NOT_FOUND, "Docking Station"),
                data=None
            )
            
        operating_times = operating_time_service.get_by_terminal(id)
        exceptions = exception_service.get_by_terminal(id)
        t = TerminalOutSchema.from_queryset(terminal, many=False, raw_measurements=True)
        operating = []
        for item in operating_times:
            operating.append(TerminalOperatingTimeOutSchema.from_queryset(item, many=False, auto_resolve_fields=False))
        t['operating_times'] = operating
        exceptions_times = []
        for item in exceptions:
            exceptions_times.append(TerminalExceptionOutSchema.from_queryset(item, many=False, auto_resolve_fields=False))
        t['exceptions'] = exceptions_times
            
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_TERMINAL_DETAIL_SUCCESS),
            data=t
        )

    @route.post('', auth=CustomJWTAuth())
    @path_permission("create", path_override='/docking-stations')
    def create_docking_station(self, request, data: str = Form(..., description="JSON string của TerminalCreateSchema"), avatar: Optional[UploadedFile] = File(None)):
        try:
            data_dict = json.loads(data)   
            schema = TerminalCreateSchema(**data_dict)  
            validated_data = schema.dict(exclude_unset=True)
        except Exception as e:
            return BaseResponse(
                status_code=422,
                message=str(e),
                data=None
            )
        if Terminal.objects.filter(code=validated_data.get('code')).exists():
            return BaseResponse(
                status_code=400,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.DOCKING_STATION_CODE_ALREADY_EXISTS),
                data=None
            )
        success, result = terminal_service.create_terminal(validated_data, avatar, request)
        if not success:
            return BaseResponse(
                status_code=400,
                message=str(result),
                data=None
            )
            
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.CREATE_DOCKING_STATION_SUCCESS),
            data=TerminalOutSchema.from_queryset(result)
        )

    @route.put('/{id}', auth=CustomJWTAuth())
    @path_permission("update", path_override='/docking-stations')
    def update_docking_station(self, id: int, request, data: str = Form(..., description="JSON string của TerminalUpdateSchema"),
                              avatar: Optional[UploadedFile] = File(None)):
        try:
            data_dict = json.loads(data)
            schema = TerminalUpdateSchema(**data_dict)  
            validated_data = schema.dict(exclude_unset=True)
        except Exception as e:
            return BaseResponse(
                status_code=422,
                message=str(e),
                data=None
            )
        if Terminal.objects.filter(code=validated_data.get('code')).exclude(id=id).exists():
            return BaseResponse(
                status_code=400,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.DOCKING_STATION_CODE_ALREADY_EXISTS),
                data=None
            )
        success, result = terminal_service.update_terminal(id, validated_data, avatar,  request)
        if not success:
            return BaseResponse(
                status_code=400,
                message=str(result),
                data=None
            )
            
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.UPDATE_DOCKING_STATION_SUCCESS),
            data=TerminalOutSchema.from_queryset(result)
        )
    
    @route.put('/{ids}/activate', auth=CustomJWTAuth())
    @path_permission("update", path_override='/docking-stations')
    def activate(self, ids: str):
        success, result = terminal_service.activate(ids)
        if not success:
            return BaseResponse(
                status_code=400,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_ACTIVATE_FAILED),
                data=None
            )
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_ACTIVATE_SUCCESS),
        )
    
    @route.put('/{ids}/deactivate', auth=CustomJWTAuth())
    @path_permission("update", path_override='/docking-stations')
    def deactivate(self, ids: str, data: TerminalDeactivateSchema = Body(None)):
        deactivate_reason_id = data.deactivate_reason_id if data else None
        success, result = terminal_service.deactivate(ids, deactivate_reason_id)
        if not success:
            return BaseResponse(
                status_code=400,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DEACTIVATE_FAILED),
                data=None
            )
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DEACTIVATE_SUCCESS),
        )


@api_controller('/infrastructures', tags=['Terminals'])
class InfrastructureController:
    @route.get('')
    @path_permission("read", path_override='/infrastructure')
    def list_infrastructures(
        self, 
        request,
        recipient_city_province: str = None,
        recipient_city_county_district: str = None,
        recipient_ward_town_township: str = None,
        recipient_street_address: str = None,
        is_active: bool = None,
        page_size: int = 25,
        current_page: int = 1,
        terminal_purpose__name: str = None,
    ):
        """
        Get paginated list of infrastructure terminals with optional filtering and sorting
        
        Parameters:
        - page_size: Number of items per page
        - current_page: Current page number
        - sort_obj: JSON string for sorting (e.g. {"field": "created_on", "order": "desc"})
        """
        page_size = int(request.GET.get('page_size', 25))
        current_page = int(request.GET.get('current_page', 1))
        
        terminals = terminal_service.get_infrastructure_terminals()
                
        query = filter_mensurement(terminals, Terminal, request)
        query = apply_dynamic_filters(query, request, [], request.GET.get('sort_obj'))

        language = get_current_request().user.language.code if get_current_request().user.language else 'en'
        # 🚀 OPTIMIZED: Use OptimizedPaginator to automatically optimize COUNT query
        paginator = OptimizedPaginator(query, page_size)
        pages = paginator.page(current_page)
        
        # OPTIMIZATION: Sử dụng MeasurableDynamicSchema với bulk measurement loading
        data = TerminalOutSchema.from_queryset(
            pages.object_list, 
            many=True, 
        )
     
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_LIST_TERMINAL_SUCCESS),
            data=data,
            total_pages=paginator.num_pages,
            total_items=paginator.count,
            current_page=current_page
        )
        
    @route.get('/{id}')
    @path_permission("read", path_override='/infrastructure')
    def get_infrastructure(self, id: int):
        terminal = terminal_service.get_terminal(id)
        
        if not terminal or not terminal.first().functions.filter(function_type='infrastructure').exists():
            return BaseResponse(
                status_code=404,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.NOT_FOUND, "Infrastructure"),
                data=None
            )
            
        operating_times = operating_time_service.get_by_terminal(id)
        exceptions = exception_service.get_by_terminal(id)
        t = TerminalOutSchema.from_queryset(terminal, many=False, raw_measurements=True)
        operating = []
        for item in operating_times:
            operating.append(TerminalOperatingTimeOutSchema.from_queryset(item, many=False, auto_resolve_fields=False))
        t['operating_times'] = operating
        exceptions_times = []
        for item in exceptions:
            exceptions_times.append(TerminalExceptionOutSchema.from_queryset(item, many=False, auto_resolve_fields=False))
        t['exceptions'] = exceptions_times
            
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_TERMINAL_DETAIL_SUCCESS),
            data=t
        )

    @route.post('', auth=CustomJWTAuth())
    @path_permission("create", path_override='/infrastructure')
    def create_infrastructure(self, request, data: str = Form(..., description="JSON string của TerminalCreateSchema"), avatar: Optional[UploadedFile] = File(None)):
        try:
            data_dict = json.loads(data)
            schema = TerminalCreateSchema(**data_dict)  
            validated_data = schema.dict(exclude_unset=True)
        except Exception as e:
            return BaseResponse(
                status_code=422,
                message=str(e),
                data=None
            )
        if Terminal.objects.filter(code=validated_data.get('code')).exists():
            return BaseResponse(
                status_code=400,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.INFRASTRUCTURE_CODE_ALREADY_EXISTS),
                data=None
            )
        success, result = terminal_service.create_terminal(validated_data, avatar, request)
        if not success:
            return BaseResponse(
                status_code=400,
                message=str(result),
                data=None
            )
            
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.CREATE_INFRASTRUCTURE_SUCCESS),
            data=TerminalOutSchema.from_queryset(result)
        )

    @route.put('/{id}', auth=CustomJWTAuth())
    @path_permission("update", path_override='/infrastructure')
    def update_infrastructure(self, id: int, request, data: str = Form(..., description="JSON string của TerminalUpdateSchema"),
                             avatar: Optional[UploadedFile] = File(None)):
        try:
            terminal = terminal_service.get_terminal(id)
            if not terminal or not terminal.first().functions.filter(function_type='infrastructure').exists():
                return BaseResponse(
                    status_code=404,
                    message=MESSAGE_ENUM.get(MESSAGE_ENUM.NOT_FOUND, "Infrastructure"),
                    data=None
                )

            data_dict = json.loads(data)
            schema = TerminalUpdateSchema(**data_dict)  
            validated_data = schema.dict(exclude_unset=True)
        except Exception as e:
            return BaseResponse(
                status_code=422,
                message=str(e),
                data=None
            )
        if Terminal.objects.filter(code=validated_data.get('code')).exclude(id=id).exists():
            return BaseResponse(
                status_code=400,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.INFRASTRUCTURE_CODE_ALREADY_EXISTS),
                data=None
            )
        success, result = terminal_service.update_terminal(id, validated_data, avatar, request)
        if not success:
            return BaseResponse(
                status_code=400,
                message=str(result),
                data=None
            )
            
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.UPDATE_INFRASTRUCTURE_SUCCESS),
            data=TerminalOutSchema.from_queryset(result)
        )

    @route.put('/{ids}/activate', auth=CustomJWTAuth())
    @path_permission("update", path_override='/infrastructure')
    def activate(self, ids: str):
        success, result = terminal_service.activate(ids)
        if not success:
            return BaseResponse(
                status_code=400,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_ACTIVATE_FAILED),
                data=None
            )
        return BaseResponse(status_code=200,message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_ACTIVATE_SUCCESS))
    
    @route.put('/{ids}/deactivate', auth=CustomJWTAuth())
    @path_permission("update", path_override='/infrastructure')
    def deactivate(self, ids: str, data: TerminalDeactivateSchema = Body(None)):
        deactivate_reason_id = data.deactivate_reason_id if data else None
        success, result = terminal_service.deactivate(ids, deactivate_reason_id)
        if not success:
            return BaseResponse(
                status_code=400,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DEACTIVATE_FAILED),
                data=None
            )
        return BaseResponse(status_code=200,message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DEACTIVATE_SUCCESS))


@api_controller('/functions', tags=['Functions'])
class FunctionController:
    @route.get('')
    @path_permission("read")
    def list_functions(self, request):
        page_size = int(request.GET.get('page_size', 25))
        current_page = int(request.GET.get('current_page', 1))
        
        functions = function_service.get_functions()
        query = build_dynamic_query_from_queryset(functions, request.GET)
        functions = functions.filter(query)
        
        # 🚀 OPTIMIZED: Use OptimizedPaginator to automatically optimize COUNT query
        paginator = OptimizedPaginator(functions, page_size)
        pages = paginator.page(current_page)
   
        data = FunctionOutSchema.from_queryset(pages.object_list, many=True)
        
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_LIST_TERMINAL_TYPE_SUCCESS),
            data=data,
            total_pages=paginator.num_pages,
            total_items=paginator.count,
            current_page=current_page
        )

    @route.get('/{id}')
    @path_permission("read")
    def get_function(self, id: int):
        function = function_service.get_function(id)
        if not function:
            return BaseResponse(
                status_code=404,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.NOT_FOUND, "Function"),
                data=None
            )
            
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_TERMINAL_TYPE_DETAIL_SUCCESS),
            data=FunctionOutSchema.from_queryset(function)
        )

    @route.post('', auth=CustomJWTAuth())
    @path_permission("create")
    def create_function(self, data: FunctionInSchema):
        success, result = function_service.create_function(data)
        if not success:
            return BaseResponse(
                status_code=400,
                message=str(result),
                data=None
            )
            
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.CREATE_TERMINAL_TYPE_SUCCESS),
            data=FunctionOutSchema.from_queryset(result)
        )

    @route.put('/{id}', auth=CustomJWTAuth())
    @path_permission("update")
    def update_function(self, id: int, data: FunctionInSchema):
        success, result = function_service.update_function(id, data)
        if not success:
            return BaseResponse(
                status_code=400,
                message=str(result),
                data=None
            )
            
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.UPDATE_TERMINAL_TYPE_SUCCESS),
            data=FunctionOutSchema.from_queryset(result)
        )

    @route.delete('/{id}', auth=CustomJWTAuth())
    @path_permission("delete")
    def delete_function(self, id: int):
        success, result = function_service.delete_function(id)
        if not success:
            return BaseResponse(
                status_code=400,
                message=str(result),
                data=None
            )
            
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DELETE_SUCCESS),
            data=None
        )


@api_controller('/terminal-types', tags=['Terminal Types'])
class TerminalTypeController:
    @route.get('')
    # @path_permission("read")
    def list_terminal_types(self, request):
        page_size = int(request.GET.get('page_size', 25))
        current_page = int(request.GET.get('current_page', 1))
        
        terminal_types = terminal_type_service.get_terminal_types()
        query = build_dynamic_query_from_queryset(terminal_types, request.GET)
        terminal_types = terminal_types.filter(query)
        
        # 🚀 OPTIMIZED: Use OptimizedPaginator to automatically optimize COUNT query
        paginator = OptimizedPaginator(terminal_types, page_size)
        pages = paginator.page(current_page)
   
        data = TerminalTypeOutSchema.from_queryset(pages.object_list, many=True)
        
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_LIST_TERMINAL_TYPE_SUCCESS),
            data=data,
            total_pages=paginator.num_pages,
            total_items=paginator.count,
            current_page=current_page
        )

    @route.get('/{id}')
    # @path_permission("read")
    def get_terminal_type(self, id: int):
        terminal_type = terminal_type_service.get_terminal_type(id)
        if not terminal_type:
            return BaseResponse(
                status_code=404,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.NOT_FOUND, "Terminal type"),
                data=None
            )
            
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_TERMINAL_TYPE_DETAIL_SUCCESS),
            data=TerminalTypeOutSchema.from_queryset(terminal_type)
        )

    @route.post('', auth=CustomJWTAuth())
    # @path_permission("create")
    def create_terminal_type(self, data: TerminalTypeInSchema):
        success, result = terminal_type_service.create_terminal_type(data)
        if not success:
            return BaseResponse(
                status_code=400,
                message=str(result),
                data=None
            )
            
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.CREATE_TERMINAL_TYPE_SUCCESS),
            data=TerminalTypeOutSchema.from_queryset(result)
        )

    @route.put('/{id}', auth=CustomJWTAuth())
    # @path_permission("update")
    def update_terminal_type(self, id: int, data: TerminalTypeInSchema):
        success, result = terminal_type_service.update_terminal_type(id, data)
        if not success:
            return BaseResponse(
                status_code=400,
                message=str(result),
                data=None
            )
            
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.UPDATE_TERMINAL_TYPE_SUCCESS),
            data=TerminalTypeOutSchema.from_queryset(result)
        )

    @route.delete('/{id}', auth=CustomJWTAuth())
    # @path_permission("delete")
    def delete_terminal_type(self, id: int):
        success, result = terminal_type_service.delete_terminal_type(id)
        if not success:
            return BaseResponse(
                status_code=400,
                message=str(result),
                data=None
            )
            
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DELETE_SUCCESS),
            data=None
        ) 
    @route.put('/{ids}/change-status', auth=CustomJWTAuth())
    @path_permission("update", path_override=['/terminals', '/delivery-hubs', '/infrastructure', '/docking-stations'])
    def change_status(self, ids: str):
        success, result = terminal_service.change_status(ids)
        if not success:
            return BaseResponse(
                status_code=400,
                message=str(result),
                data=None,
                success=False
            )
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.CHANGE_STATUS_SUCCESS),
            data=None,
            success=True
        )
    
@api_controller('/delivery-hubs', tags=['Delivery Hubs'])
class DeliveryHubController:
    @route.get('')
    @path_permission("read", path_override='/delivery-hubs')
    def list_delivery_hubs(self, request):
        page_size = int(request.GET.get('page_size', 25))
        current_page = int(request.GET.get('current_page', 1))
        delivery_hubs = delivery_hub_service.get_delivery_hubs()
        query = filter_mensurement(delivery_hubs, Terminal, request)
        query = apply_dynamic_filters(query, request, [], request.GET.get('sort_obj'))
        
        language = get_current_request().user.language.code if get_current_request().user.language else 'en'
        # 🚀 OPTIMIZED: Use OptimizedPaginator to automatically optimize COUNT query
        paginator = OptimizedPaginator(query, page_size)
        pages = paginator.page(current_page)
        
        # OPTIMIZATION: Sử dụng MeasurableDynamicSchema với bulk measurement loading
        data = TerminalOutSchema.from_queryset(
            pages.object_list, 
            many=True, 
        )
        
        # OPTIMIZATION: Bulk update additional fields cho tất cả terminals
        if hasattr(data, '__iter__') and len(data) > 0:
            for i, terminal in enumerate(pages.object_list):
                # Update full_address
                data[i]['full_address'] = f"{terminal.street_address}, {terminal.ward_town_township}, {terminal.city_county_district}, {terminal.city_province}"
                
                # Update terminal types
                if terminal.terminal_types.exists():
                    first_type = terminal.terminal_types.first()
                    data[i]['type'] = first_type.get_translation('name', language)
                    data[i]['terminal_type__name'] = first_type.get_translation('name', language)
                    data[i]['terminal_type'] = first_type.get_translation('name', language)
                    data[i]['terminal_type__description'] = first_type.get_translation('description', language)

                # Update location type
                if terminal.location_type:
                    data[i]['location_type'] = terminal.location_type.get_translation('name', language)
                    data[i]['location_type__name'] = terminal.location_type.get_translation('name', language)
                    data[i]['location_type__description'] = terminal.location_type.get_translation('description', language)

        # filter by address if request payload has full_address
        if request.GET.get('full_address'):
            data = [t for t in data if request.GET.get('full_address') in t['full_address']]
        # sort data by full_address if request payload has sort_obj and key is full_address [{"key":"full_address","value":"desc"}]
        if request.GET.get('sort_obj'):
            sort_obj = json.loads(request.GET.get('sort_obj'))
            if sort_obj[0]['key'] == 'full_address':
                data = sorted(data, key=lambda x: x['full_address'], reverse=sort_obj[0]['value'] == 'desc')
     
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_LIST_TERMINAL_SUCCESS),
            data=data,
            total_pages=paginator.num_pages,
            total_items=paginator.count,
            current_page=current_page
        )
    
    @route.get('/{id}')
    @path_permission("read", path_override='/delivery-hubs')
    def get_delivery_hub(self, id: int):
        terminal = terminal_service.get_terminal(id)
        
        if not terminal or not terminal.first().terminal_types.filter(code='DELIVERY_HUB').exists():
            return BaseResponse(
                status_code=404,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.NOT_FOUND, "Delivery Hub"),
                data=None
            )
            
        operating_times = operating_time_service.get_by_terminal(id)
        exceptions = exception_service.get_by_terminal(id)
        t = TerminalOutSchema.from_queryset(terminal, many=False, raw_measurements=True)
        operating = []
        for item in operating_times:
            operating.append(TerminalOperatingTimeOutSchema.from_queryset(item, many=False, auto_resolve_fields=False))
        t['operating_times'] = operating
        exceptions_times = []
        for item in exceptions:
            exceptions_times.append(TerminalExceptionOutSchema.from_queryset(item, many=False, auto_resolve_fields=False))
        t['exceptions'] = exceptions_times
        
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_DELIVERY_HUB_DETAIL_SUCCESS),
            data=t
        )
    
    @route.post('', auth=CustomJWTAuth())
    @path_permission("create", path_override='/delivery-hubs')
    def create_delivery_hub(self, request, data: str = Form(..., description="JSON string của TerminalCreateSchema"), avatar: Optional[UploadedFile] = File(None)):
        try:
            data_dict = json.loads(data)
            schema = TerminalCreateSchema(**data_dict)  
            validated_data = schema.dict(exclude_unset=True)
        except Exception as e:
            return BaseResponse(
                status_code=422,
                message=str(e),
                data=None
            )
        if Terminal.objects.filter(code=validated_data.get('code')).exists():
            return BaseResponse(
                status_code=400,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.DELIVERY_HUB_CODE_ALREADY_EXISTS),
                data=None
            )
        success, result = delivery_hub_service.create_delivery_hub(validated_data, avatar, request)
        if not success:
            return BaseResponse(
                status_code=400,
                message=str(result),
                data=None
            )
            
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.CREATE_DELIVERY_HUB_SUCCESS),
            data=TerminalOutSchema.from_queryset(result)
        )

    @route.put('/{id}', auth=CustomJWTAuth())
    @path_permission("update", path_override='/delivery-hubs')
    def update_delivery_hub(self, id: int, request, data: str = Form(..., description="JSON string của TerminalUpdateSchema"),
                              avatar: Optional[UploadedFile] = File(None)):
        try:
            terminal = terminal_service.get_terminal(id)
            if not terminal or not terminal.first().terminal_types.filter(code='DELIVERY_HUB').exists():
                return BaseResponse(
                    status_code=404,
                    message=MESSAGE_ENUM.get(MESSAGE_ENUM.NOT_FOUND, "Delivery Hub"),
                    data=None
                )
                
            data_dict = json.loads(data)
            schema = TerminalUpdateSchema(**data_dict)  
            validated_data = schema.dict(exclude_unset=True)
        except Exception as e:
            return BaseResponse(
                status_code=422,
                message=str(e),
                data=None
            )
        if Terminal.objects.filter(code=validated_data.get('code')).exclude(id=id).exists():
            return BaseResponse(
                status_code=400,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.DELIVERY_HUB_CODE_ALREADY_EXISTS),
                data=None
            )
        success, result = terminal_service.update_terminal(id, validated_data, avatar,  request)
        if not success:
            return BaseResponse(
                status_code=400,
                message=str(result),
                data=None
            )
            
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.UPDATE_DELIVERY_HUB_SUCCESS),
            data=TerminalOutSchema.from_queryset(result)
        )
    
    @route.put('/{ids}/activate', auth=CustomJWTAuth())
    @path_permission("update", path_override='/delivery-hubs')
    def activate(self, ids: str):
        success, result = terminal_service.activate(ids)
        if not success:
            return BaseResponse(
                status_code=400,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_ACTIVATE_FAILED),
                data=None
            )
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_ACTIVATE_SUCCESS),
        )
    
    @route.put('/{ids}/deactivate', auth=CustomJWTAuth())
    @path_permission("update", path_override='/delivery-hubs')
    def deactivate(self, ids: str, data: TerminalDeactivateSchema = Body(None)):
        deactivate_reason_id = data.deactivate_reason_id if data else None
        success, result = terminal_service.deactivate(ids, deactivate_reason_id)
        if not success:
            return BaseResponse(
                status_code=400,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DEACTIVATE_FAILED),
                data=None
            )
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DEACTIVATE_SUCCESS),
        )

@api_controller('/location-types', tags=['Location Types'])
class LocationTypeController:
    @route.get('', auth=CustomJWTAuth())
    def list_location_types(self, request):
        page_size = int(request.GET.get('page_size', 25))
        current_page = int(request.GET.get('current_page', 1))
        
        location_types = location_type_service.get_location_types()
        query = build_dynamic_query_from_queryset(location_types, request.GET)
        location_types = location_types.filter(query)
        
        # 🚀 OPTIMIZED: Use OptimizedPaginator to automatically optimize COUNT query
        paginator = OptimizedPaginator(location_types, page_size)
        pages = paginator.page(current_page)
   
        data = LocationTypeOutSchema.from_queryset(pages.object_list, many=True)
        
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_LIST_LOCATION_TYPE_SUCCESS),
            data=data,
            total_pages=paginator.num_pages,
            total_items=paginator.count,
            current_page=current_page
        )
    
@api_controller('/functions', tags=['Functions'])
class FunctionController:
    @route.get('', auth=CustomJWTAuth())
    # @path_permission("read")
    def list_functions(self, request):
        page_size = int(request.GET.get('page_size', 25))
        current_page = int(request.GET.get('current_page', 1))
        functions = function_service.get_functions()
        functions = apply_dynamic_filters(functions, request, [], request.GET.get('sort_obj'))
            
        # 🚀 OPTIMIZED: Use OptimizedPaginator to automatically optimize COUNT query
        paginator = OptimizedPaginator(functions, page_size)
        pages = paginator.page(current_page)
        
        data = FunctionOutSchema.from_queryset(pages.object_list, many=True)
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_LIST_FUNC_TYPE_SUCCESS),
            data=data,
            total_pages=paginator.num_pages,
            total_items=paginator.count,
            current_page=current_page
        )

    @route.get('/function-types')
    # @path_permission("read")
    def get_function_types(self, request, function_types: str = None):
        current_page = int(request.GET.get('current_page', 1))
        page_size = int(request.GET.get('page_size', 25))
        function_types = [f for f in request.GET.get('function_types', None).split(',')]
       
        function_types = function_service.get_functions_by_type(function_types)
        
        query = apply_dynamic_filters(function_types, request, [], request.GET.get('sort_obj'))
        
        function_types = query
       
        # 🚀 OPTIMIZED: Use OptimizedPaginator to automatically optimize COUNT query
        paginator = OptimizedPaginator(function_types, page_size)
        pages = paginator.page(current_page)
        data = FunctionTypeOutSchema.from_queryset(pages.object_list, many=True, auto_resolve_fields=False)
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_FUNC_TYPE_DETAIL_SUCCESS),
            data=data,
            total_pages=paginator.num_pages,
            total_items=paginator.count,
            current_page=current_page
        )

    @route.delete('/{id}', auth=CustomJWTAuth())
    # @path_permission("delete")
    def delete_function(self, id: int):
        success, result = function_service.delete_function(id)
        if not success:
            return BaseResponse(
                status_code=400,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DELETE_FAILED) + " - " + str(result),
                data=None
            )
        return BaseResponse(status_code=200,message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DELETE_SUCCESS))