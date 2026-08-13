from core.file_management.helper import FileHelper
from ninja import File, Form
from ninja_extra import api_controller, route
from ninja.files import UploadedFile
from typing import List, Optional
from ninja.errors import ValidationError
from common.pagination import OptimizedPaginator
import math
import json

from devices.utils import convert_unit, filter_mensurement
from terminals.utils import calculate_distance_km


from terminals.models import Routes
from terminals.schemas.schemas_djantic_in import RouteCreateSchema, RouteUpdateSchema
from terminals.schemas.schemas_djantic_out import RouteOutSchema, TerminalOutSchema
from terminals.services import routes_service
from terminals.tasks import upload_route_images
from core.api.v1.auth import CustomJWTAuth
from core.common.base_response import BaseResponse
from core.common.search.dynamic_search import build_dynamic_query_from_queryset, apply_dynamic_filters
from common.constant import MESSAGE_ENUM
from core.role.permission import path_permission

@api_controller('/routes', tags=['Routes'])
class RoutesController:

    def extract_altitude_from_command_line(self, command_line):
        """
        Extract operating altitude from command_line waypoint params array
        Returns the last index (altitude) from WAYPOINT params
        """
        if not command_line or not isinstance(command_line, dict):
            return 0
        
        for command_id, command_data in command_line.items():
            if isinstance(command_data, dict):
                for command_name, params in command_data.items():
                    if len(params) >= 7:
                        try:
                            return float(params[6]) if params[6] is not None else 0
                        except (ValueError, TypeError):
                            return 0
        return 0
    @route.get('',  auth=CustomJWTAuth())
    @path_permission("read", path_override="/routes")
    def list_routes(self, request):
        page_size = int(request.GET.get('page_size', 25))
        current_page = int(request.GET.get('current_page', 1))
        
        routes = routes_service.get_routes()
        query = filter_mensurement(routes, Routes, request)
        query = apply_dynamic_filters(query, request, [], request.GET.get('sort_obj'))

        
        # 🚀 OPTIMIZED: Use OptimizedPaginator to automatically optimize COUNT query
        paginator = OptimizedPaginator(query, page_size)
        pages = paginator.page(current_page)
   
        datas = pages.object_list
        # measurements_fields = ['total_distance', 'estimated_time']
        # results = []
        # for data in datas:
        #     route = RouteOutSchema.from_queryset(data)
        #     for measurement in measurements_fields:
        #         m = data.measurements.filter(measurement_type=measurement).first()
        #         if m:
        #             route[measurement] = m.get_formatted_value(None)
        #     results.append(route)   
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_LIST_ROUTE_SUCCESS),
            data=RouteOutSchema.from_queryset(datas, many=True),
            total_pages=paginator.num_pages,
            total_items=paginator.count,
            current_page=current_page
        )

    @route.get('/{id}', auth=CustomJWTAuth())
    @path_permission("read", path_override="/routes")
    def get_route(self, id: int, edit: bool=False):
        route = routes_service.get_route(id)
        if not route:
            return BaseResponse(
                status_code=404,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_ROUTE_DETAIL_SUCCESS),
                data=None
            )
        
        data = RouteOutSchema.from_queryset(route)
        measurements_fields = ['total_distance', 'estimated_time']
        # 🚀 OPTIMIZED: Sử dụng prefetched measurements thay vì query lại
        # Measurements đã được prefetch trong service, chỉ cần filter trong memory
        for measurement in measurements_fields:
            try:
                # Sử dụng prefetched measurements (đã được load trong memory)
                m = next((m for m in route.measurements.all() if m.measurement_type == measurement), None)
                if m and edit:
                    data[measurement] = m.get_formatted_value(None)
                elif m:
                    data[measurement] = m.get_converted_data(None)
            except Exception as e:
                print(e)
        
        route_terminals = []
        # 🚀 OPTIMIZED: Sử dụng prefetched route_terminals (đã được load trong memory)
        all_terminals = list(route.route_terminals.all()) if route else []
        
        for terminal in all_terminals:
            # 🚀 OPTIMIZED: Cache measurements theo measurement_type để tránh iterate lại nhiều lần
            # Measurements đã được prefetch, chỉ cần filter trong memory một lần
            terminal_measurements_cache = {m.measurement_type: m for m in terminal.terminal.measurements.all()}
            route_terminal_measurements_cache = {m.measurement_type: m for m in terminal.measurements.all()}
            
            time_stops = terminal_measurements_cache.get("time_stops")
            cruise_speed = route_terminal_measurements_cache.get("cruise_speed")
            operating_altitude = route_terminal_measurements_cache.get("operating_altitude")
            
            if time_stops:
                time_stops = convert_unit(time_stops.data.get('value'), time_stops.data.get('unit'), 's') or 0
            else:
                time_stops = 0
            if cruise_speed:
                cruise_speed = cruise_speed.get_numeric_value(user_units=None) or 0
            else:
                cruise_speed = 0
            if operating_altitude:
                operating_altitude = operating_altitude.get_numeric_value(user_units=None) or 0
            else:
                operating_altitude = 0
            # Build address from non-empty fields only
            if terminal.stop:
                address_parts = []
                if terminal.terminal.city_province:
                    address_parts.append(terminal.terminal.city_province)
                if terminal.terminal.city_county_district:
                    address_parts.append(terminal.terminal.city_county_district)
                if terminal.terminal.ward_town_township:
                    address_parts.append(terminal.terminal.ward_town_township)
                if terminal.terminal.street_address:
                    address_parts.append(terminal.terminal.street_address)
                
                address = ", ".join(address_parts) if address_parts else ""
            else:
                address = ""
            # 🚀 OPTIMIZED: terminal_types đã được prefetch, sử dụng list() để tránh query lại
            terminal_types = list(terminal.terminal.terminal_types.all()) if hasattr(terminal.terminal, 'terminal_types') else []
            route_terminals.append({
                "route_terminal_id": terminal.id,
                "terminal_id": terminal.terminal.id,
                "name": terminal.terminal.name,
                "terminal_type__name": (", ".join([t.name for t in terminal_types]) if terminal_types else None),
                "address": address,
                "latitude": terminal.terminal.latitude,
                "longitude": terminal.terminal.longitude,
                "note": terminal.terminal.note,
                "stop": terminal.stop,
                "order": terminal.order,
                "time_stops": time_stops,
                "for_robot": terminal.for_robot,
                "cruise_speed": cruise_speed,
                "operating_altitude": operating_altitude,
                "command_line": terminal.command_line,
                "frame": terminal.frame
            }) 
        
        # Prepare chart data for Recharts format
        chart_data = []
        # 🚀 OPTIMIZED: Sử dụng lại all_terminals đã được load, không query lại
        # Sort terminals by order to calculate distance correctly
        sorted_terminals = sorted(all_terminals, key=lambda x: x.order)
        
        for i, terminal in enumerate(sorted_terminals):
            # 🚀 OPTIMIZED: Cache measurements một lần và tái sử dụng
            # Measurements đã được prefetch trong vòng lặp trên, chỉ cần filter lại
            route_terminal_measurements_cache = {m.measurement_type: m for m in terminal.measurements.all()}
            cruise_speed_measurement = route_terminal_measurements_cache.get("cruise_speed")
            cruise_speed_value = cruise_speed_measurement.get_numeric_value(user_units='m/s') if cruise_speed_measurement else 0
            
            # Calculate distance from previous terminal
            distance = 0
            if i > 0:  # Not the first terminal
                prev_terminal = sorted_terminals[i-1]
                distance = calculate_distance_km(
                    prev_terminal.terminal.latitude,
                    prev_terminal.terminal.longitude,
                    terminal.terminal.latitude,
                    terminal.terminal.longitude
                )
            
            # Extract altitude from command_line waypoint (last index of params array)
            operating_altitude = self.extract_altitude_from_command_line(terminal.command_line)
            if terminal.terminal.name == "Set Servo" or (terminal.command_line and isinstance(terminal.command_line, dict) and list(terminal.command_line.keys()) == ["183"]):
                continue
            chart_data.append({
                "name": terminal.terminal.name,
                "cruise_speed": round(cruise_speed_value, 2),
                "operating_altitude": operating_altitude,
                "order": terminal.order,
                "distance": round(distance, 2)
            })
        
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_ROUTE_DETAIL_SUCCESS),
            data={
                "route": data,
                "route_terminals": route_terminals,
                "chart_data": chart_data
            }
        )

    @route.post('', auth=CustomJWTAuth())
    @path_permission("create", path_override="/routes")
    def create_route(self, request, data: str = Form(..., description="JSON string của RouteCreateSchema"), img_map: Optional[UploadedFile] = File(None), img_route: Optional[UploadedFile] = File(None)):
        data_dict = json.loads(data)
        schema = RouteCreateSchema(**data_dict)  
        validated_data = schema.dict(exclude_unset=True)
        success, result = routes_service.create_route(validated_data)
        if not success:
            return BaseResponse(
                status_code=400,
                message=str(result),
                data=None
            )
        # Upload images asynchronously (avoid blocking request on MinIO/S3 latency)
        img_map_data = None
        img_route_data = None
        if img_map:
            img_map.seek(0)
            img_map_data = {
                "content": img_map.read(),
                "name": getattr(img_map, "name", "map.png"),
                "content_type": getattr(img_map, "content_type", "image/png"),
            }
        if img_route:
            img_route.seek(0)
            img_route_data = {
                "content": img_route.read(),
                "name": getattr(img_route, "name", "route.png"),
                "content_type": getattr(img_route, "content_type", "image/png"),
            }
        if img_map_data or img_route_data:
            upload_route_images.apply_async(args=[result.id, request.user.id, img_map_data, img_route_data])
            
        # Get the complete route with relationships
        created_route = routes_service.get_route(result.id)
        
      
            
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.CREATE_ROUTE_SUCCESS),
            data=RouteOutSchema.from_queryset(created_route) 
        )

    @route.put('/{id}', auth=CustomJWTAuth())
    @path_permission("update", path_override="/routes")
    def update_route(self,request, id: int, data: str = Form(..., description="JSON string của RouteUpdateSchema"), img_map: Optional[UploadedFile] = File(None), img_route: Optional[UploadedFile] = File(None)):
        data_dict = json.loads(data)
        schema = RouteUpdateSchema(**data_dict)  
        validated_data = schema.dict(exclude_unset=True)
        success, result = routes_service.update_route(id, validated_data)
        if not success:
            return BaseResponse(
                status_code=400,
                message=str(result),
                data=None
            )
        # Upload images asynchronously (avoid blocking request on MinIO/S3 latency)
        img_map_data = None
        img_route_data = None
        if img_map:
            img_map.seek(0)
            img_map_data = {
                "content": img_map.read(),
                "name": getattr(img_map, "name", "map.png"),
                "content_type": getattr(img_map, "content_type", "image/png"),
            }
        if img_route:
            img_route.seek(0)
            img_route_data = {
                "content": img_route.read(),
                "name": getattr(img_route, "name", "route.png"),
                "content_type": getattr(img_route, "content_type", "image/png"),
            }
        if img_map_data or img_route_data:
            upload_route_images.apply_async(args=[id, request.user.id, img_map_data, img_route_data])
        # NOTE: Avoid expensive re-fetch with heavy prefetch here.
        # Client can call GET /routes/{id} if it needs refreshed data.
            
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.UPDATE_ROUTE_SUCCESS),
            data=None
        )

    @route.delete('/delete/{ids}', auth=CustomJWTAuth())
    @path_permission("delete", path_override="/routes")
    def delete_route(self, ids: str):
      
        success, result = routes_service.delete_route(ids)
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


    @route.put('/{ids}/change-status', auth=CustomJWTAuth())
    @path_permission("update", path_override="/routes")
    def change_status(self, ids: str):
        success, result = routes_service.change_status(ids)
        if not success:
            return BaseResponse(
                status_code=400,
                message=str(result),
                data=None
            )
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.CHANGE_STATUS_SUCCESS),
            data=None
        )
    
    @route.put('/{ids}/activate', auth=CustomJWTAuth())
    @path_permission("update", path_override="/routes")
    def activate(self, ids: str):
        success, result = routes_service.activate(ids)
        if not success:
            return BaseResponse(
                status_code=400,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_ACTIVATE_FAILED),
                data=None
            )
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_ACTIVATE_SUCCESS),
            data=None
        )
    
    @route.put('/{ids}/deactivate', auth=CustomJWTAuth())
    @path_permission("update", path_override="/routes")
    def deactivate(self, ids: str):
        success, result = routes_service.deactivate(ids)
        if not success:
            return BaseResponse(
                status_code=400,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DEACTIVATE_FAILED),
                data=None
            )
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DEACTIVATE_SUCCESS),
            data=None
        )