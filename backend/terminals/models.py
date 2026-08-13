from django.db import models
from django.contrib.contenttypes.fields import GenericRelation
from core.base import BaseModel
from core.file_management.models import UserMediaFileItem, UserMediaFile
from core.user.models import Country
from core.base import BaseModelWithGroup
from devices.models import MeasurableModel
from common.measurable_model import MeasurableModelWithGroup

class TerminalType(BaseModelWithGroup):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    description = models.TextField(null=True, blank=True)
    TRANSLATABLE_FIELDS = ['name','description']
    
    class Meta:
        indexes = [
            models.Index(fields=['code']),
        ]
    
    def __str__(self):
        return self.name

class Function(BaseModelWithGroup):
    """
    Unified model to replace InfrastructureType, TerminalBaseType, and DockingStationType
    """
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=100, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    function_type = models.CharField(max_length=50, choices=[
        ('infrastructure', 'Infrastructure'),
        ('terminal_base', 'Terminal Base'),
        ('docking_station', 'Docking Station'),
    ], null=True, blank=True, help_text="Type of function for data migration purposes")
    TRANSLATABLE_FIELDS = ['name','description']
    
    def __str__(self):
        return self.name
     
class TerminalPurpose(BaseModelWithGroup):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=100, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    TRANSLATABLE_FIELDS = ['name','description']
    def __str__(self):
        return self.name
class LocationType(BaseModel):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=100, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    TRANSLATABLE_FIELDS = ['name','description']
    def __str__(self):
        return self.name
class PurposeType(BaseModel):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=100, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    TRANSLATABLE_FIELDS = ['name','description']
    def __str__(self):
        return self.name    

class DeactivateReason(BaseModel):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=100, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    TRANSLATABLE_FIELDS = ['name','description']
    def __str__(self):
        return self.name

class DayOfWeek(BaseModel):
    """
    Model để quản lý các ngày trong tuần
    Cho phép thêm/sửa/xóa và quản lý linh hoạt
    """
    name = models.CharField(max_length=50)  # Monday, Tuesday, etc.
    code = models.CharField(max_length=20, unique=True, db_index=True)  # monday, tuesday, etc.
    order = models.IntegerField(default=0, db_index=True, help_text="Thứ tự hiển thị (0=Monday, 6=Sunday)")
    description = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    TRANSLATABLE_FIELDS = ['name', 'description']
    
    class Meta:
        ordering = ['order']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['order']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return self.name
        
class Terminal(MeasurableModelWithGroup):
    name = models.CharField(max_length=255)
    code = models.CharField(null=True, blank=True, unique=True, db_index=True)
    terminal_types = models.ManyToManyField(TerminalType, related_name='terminals', blank=True)
    
    # Unified functions field to replace infrastructure_type, terminal_base_type, and docking_station_type
    functions = models.ManyToManyField(Function, related_name='terminals', blank=True, help_text="Unified functions replacing infrastructure_type, terminal_base_type, and docking_station_type")
    
    location_type = models.ForeignKey(LocationType, on_delete=models.CASCADE, related_name='terminals', null=True, blank=True)
    terminal_purpose = models.ForeignKey(TerminalPurpose, on_delete=models.CASCADE, related_name='terminals', null=True, blank=True)
    # time_stops = models.IntegerField(default=0, help_text="Time in minutes")
    latitude = models.CharField(null=True, blank=True)
    longitude = models.CharField(null=True, blank=True)
    city_province = models.CharField(max_length=255, null=True, blank=True)
    city_county_district = models.CharField(max_length=255, null=True, blank=True)
    ward_town_township = models.CharField(max_length=255, null=True, blank=True)
    street_address = models.TextField(null=True, blank=True)
    address_note = models.TextField(null=True, blank=True)
    postal_code = models.CharField(max_length=255, null=True, blank=True)
    note = models.TextField(null=True, blank=True)
    purpose_type = models.ForeignKey(PurposeType, on_delete=models.CASCADE, related_name='terminals', null=True, blank=True)
    avatar = models.ForeignKey(UserMediaFile, on_delete=models.SET_NULL, related_name='terminal_avatar', null=True, blank=True)
    active = models.BooleanField(default=True, db_index=True)
    file_attachments = GenericRelation(UserMediaFileItem)
    status = models.CharField(max_length=50, default='active', db_index=True)
    url = models.CharField(null=True, blank=True)
    manager_name = models.CharField(null=True, blank=True)
    manufacturer = models.CharField(null=True, blank=True)
    year_of_manufacture = models.CharField(null=True, blank=True)
    registration_date = models.DateField(null=True, blank=True)
    compatible_drone = models.CharField(null=True, blank=True)
    swap_time = models.CharField(null=True, blank=True)
    weather_resistant = models.CharField(null=True, blank=True)
    deactivate_reason = models.ForeignKey(DeactivateReason, on_delete=models.CASCADE, related_name='terminals', null=True, blank=True)
    MEASUREMENT_TYPES = {
        'time_stops': {'type': 'simple', 'default_unit': 'mins'},
        'weight': {'type': 'simple', 'default_unit': 'kg'},
        'temperature_range': {'type': 'range', 'default_unit': '°C'},
    }
    
    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['active']),
            models.Index(fields=['status']),
            models.Index(fields=['code', 'active']),
            models.Index(fields=['status', 'active']),
        ]
    
    def __str__(self):
        return self.name 
    
    # Helper methods dựa trên routes
    def get_related_routes(self):
        """Lấy tất cả routes mà terminal này tham gia"""
        return Routes.objects.filter(route_terminals__terminal=self).distinct()
    
    def get_related_terminals(self):
        """Lấy tất cả terminals khác nằm trong cùng routes với terminal này"""
        related_routes = self.get_related_routes()
        return Terminal.objects.filter(
            route_terminals__route__in=related_routes
        ).exclude(id=self.id).distinct()
    
    def get_terminals_in_same_routes(self):
        """Alias cho get_related_terminals để rõ nghĩa hơn"""
        return self.get_related_terminals()
    
    def get_route_neighbors(self, route_id=None):
        """Lấy các terminals liền kề trong cùng route (theo thứ tự order)"""
        if route_id:
            route_terminals = RouteTerminal.objects.filter(
                route_id=route_id
            ).order_by('order')
        else:
            # Lấy từ tất cả routes mà terminal này tham gia
            related_routes = self.get_related_routes()
            route_terminals = RouteTerminal.objects.filter(
                route__in=related_routes
            ).order_by('route', 'order')
        
        neighbors = []
        current_terminal_positions = list(route_terminals.filter(terminal=self))
        
        for current_pos in current_terminal_positions:
            route_terminals_in_route = route_terminals.filter(route=current_pos.route)
            
            # Tìm terminal trước và sau
            prev_terminal = route_terminals_in_route.filter(
                order__lt=current_pos.order
            ).order_by('-order').first()
            
            next_terminal = route_terminals_in_route.filter(
                order__gt=current_pos.order
            ).order_by('order').first()
            
            route_neighbors = {
                'route': current_pos.route,
                'current_order': current_pos.order,
                'previous': prev_terminal.terminal if prev_terminal else None,
                'next': next_terminal.terminal if next_terminal else None
            }
            neighbors.append(route_neighbors)
        
        return neighbors
    
    def get_routes_count(self):
        """Lấy số lượng routes mà terminal này tham gia"""
        return self.get_related_routes().count()
    
    def get_terminal_types_names(self):
        """Lấy danh sách tên các terminal types"""
        return list(self.terminal_types.values_list('name', flat=True))
    
    def is_start_terminal(self, route_id=None):
        """Kiểm tra xem terminal này có phải là điểm đầu trong route không"""
        if route_id:
            routes_to_check = Routes.objects.filter(id=route_id)
        else:
            routes_to_check = self.get_related_routes()
        
        for route in routes_to_check:
            first_terminal = RouteTerminal.objects.filter(
                route=route
            ).order_by('order').first()
            
            if first_terminal and first_terminal.terminal == self:
                return True
        return False
    
    def is_end_terminal(self, route_id=None):
        """Kiểm tra xem terminal này có phải là điểm cuối trong route không"""
        if route_id:
            routes_to_check = Routes.objects.filter(id=route_id)
        else:
            routes_to_check = self.get_related_routes()
        
        for route in routes_to_check:
            last_terminal = RouteTerminal.objects.filter(
                route=route
            ).order_by('-order').first()
            
            if last_terminal and last_terminal.terminal == self:
                return True
        return False
    
    def get_position_in_routes(self):
        """Lấy vị trí của terminal trong tất cả routes"""
        positions = []
        route_terminals = RouteTerminal.objects.filter(terminal=self).select_related('route')
        
        for rt in route_terminals:
            total_terminals = RouteTerminal.objects.filter(route=rt.route).count()
            positions.append({
                'route': rt.route,
                'order': rt.order,
                'total_terminals': total_terminals,
                'is_start': rt.order == 1,
                'is_end': rt.order == total_terminals
            })
        
        return positions
    
    @classmethod
    def get_terminals_by_route(cls, route_id):
        """Lấy tất cả terminals trong một route cụ thể theo thứ tự"""
        return cls.objects.filter(
            route_terminals__route_id=route_id
        ).order_by('route_terminals__order')
    
    @classmethod 
    def get_terminals_with_multiple_routes(cls):
        """Lấy tất cả terminals tham gia nhiều hơn 1 route"""
        from django.db.models import Count
        return cls.objects.annotate(
            routes_count=Count('route_terminals__route', distinct=True)
        ).filter(routes_count__gt=1)
    

class RouteService(BaseModel):
    name = models.CharField(max_length=255)
    code = models.CharField(null=True, blank=True, unique=True, db_index=True)
    description = models.TextField(null=True, blank=True)
    TRANSLATABLE_FIELDS = ['name']
class Routes(MeasurableModel):
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True, db_index=True)
    code = models.CharField(null=True, blank=True, unique=True, db_index=True)
    description = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=50, default='active', db_index=True)
    total_stops = models.IntegerField(default=0)
    route_service = models.ForeignKey(RouteService, on_delete=models.CASCADE, related_name='routes_service', null=True, blank=True)
    terminal_from = models.ForeignKey(Terminal, on_delete=models.CASCADE, related_name='terminal_from', null=True, blank=True)
    note = models.TextField(null=True, blank=True)
    two_way = models.BooleanField(default=False, null=True, blank=True)
    img_map = models.ForeignKey(UserMediaFile, on_delete=models.SET_NULL, related_name='routes_img_map', null=True, blank=True)
    img_route = models.ForeignKey(UserMediaFile, on_delete=models.SET_NULL, related_name='routes_img_route', null=True, blank=True)
    MEASUREMENT_TYPES = {
        'total_distance': {'type': 'simple', 'default_unit': 'km'},
        'estimated_time': {'type': 'simple', 'default_unit': 'mins'},
    }
    class Meta:
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['is_active']),
            models.Index(fields=['status']),
            models.Index(fields=['code', 'is_active']),
            models.Index(fields=['status', 'is_active']),
        ]
    def __str__(self):
        return self.name
    
class RouteTerminal(MeasurableModel):
    route = models.ForeignKey(Routes, on_delete=models.CASCADE, related_name='route_terminals', null=True, blank=True)
    terminal = models.ForeignKey(Terminal, on_delete=models.CASCADE, related_name='route_terminals', null=True, blank=True)
    stop = models.BooleanField(default=False)
    order = models.IntegerField(default=0)
    for_robot = models.BooleanField(default=False)
    command_line = models.JSONField(null=True, blank=True)  
    frame = models.JSONField(null=True, blank=True)
    MEASUREMENT_TYPES = {
        'cruise_speed': {'type': 'simple', 'default_unit': 'm/s'},
        'operating_altitude': {'type': 'simple', 'default_unit': 'm'},
    }


class TerminalOperatingTime(BaseModel):
    
    terminal = models.ForeignKey(Terminal, on_delete=models.CASCADE, related_name='operating_times')
    day_of_week = models.ForeignKey(DayOfWeek, on_delete=models.CASCADE, related_name='operating_times', db_index=True)
    is_active = models.BooleanField(default=False, db_index=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['terminal', 'day_of_week']
        indexes = [
            models.Index(fields=['terminal', 'day_of_week']),
            models.Index(fields=['terminal', 'is_active']),
        ]
        ordering = ['terminal', 'day_of_week__order']
    
    def __str__(self):
        return f"{self.terminal.name} - {self.day_of_week.name} ({'Active' if self.is_active else 'Inactive'})"


class TerminalException(BaseModel):
   
    terminal = models.ForeignKey(Terminal, on_delete=models.CASCADE, related_name='exceptions')
    exception_date = models.DateField(db_index=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    is_all_day = models.BooleanField(default=False, db_index=True)
    reason = models.CharField(max_length=500, null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['terminal', 'exception_date']),
            models.Index(fields=['exception_date']),
            models.Index(fields=['terminal', 'is_all_day']),
        ]
        ordering = ['terminal', 'exception_date']
    
    def __str__(self):
        return f"{self.terminal.name} - {self.exception_date} ({self.reason or 'Exception'})"

    