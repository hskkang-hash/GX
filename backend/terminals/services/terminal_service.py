from django.db import transaction
from django.core.exceptions import ValidationError
from django.db.models import F, CharField, Value, Count, Prefetch
from typing import List, Dict, Optional
from functools import lru_cache
from delivery.models import DeliveryOperation
from common.constant import MESSAGE_ENUM, get_message
from terminals.models import DeactivateReason, LocationType, RouteTerminal, Routes, Terminal, TerminalType, PurposeType, Function, TerminalOperatingTime, TerminalException


from django.db.models.functions import Coalesce, Concat
from core.file_management.helper import FileHelper
from django.db.models import OuterRef, Subquery, Count, Max, F, Case, When, BooleanField, Exists, CharField, Sum, Value, Q
from core.user.models import UserGroup
# Import StringAgg for PostgreSQL, fallback for other databases


# backend/terminals/services/terminal_service.py

# 🚀 PERFORMANCE: Cache translations to avoid repeated DB queries
_translation_cache: Dict[str, Dict[int, str]] = {}
_translation_cache_fallback: Dict[str, Dict[int, str]] = {}

def _load_translations_batch(content_type_model, field_name: str, language_code: str) -> Dict[int, str]:
    """
    🚀 BATCH LOAD: Load all translations for a model/field in one query.
    Returns mapping: {object_id: translated_value}
    """
    cache_key = f"{content_type_model.__name__}.{field_name}.{language_code}"
    
    # Check cache first
    if cache_key in _translation_cache:
        return _translation_cache[cache_key]
    
    from django.contrib.contenttypes.models import ContentType
    from core.multilanguage.models import MultiLanguageContent
    import json
    
    try:
        content_type = ContentType.objects.get_for_model(content_type_model)
        
        # 🚀 BATCH: Load ALL translations in ONE query
        translations_data = MultiLanguageContent.objects.filter(
            content_type=content_type,
            field_name=field_name
        ).values('object_id', 'translations')
        
        # Build mapping for selected language and fallback
        translation_mapping = {}
        fallback_mapping = {}
        
        for item in translations_data:
            try:
                translations = json.loads(item['translations'])
                object_id = item['object_id']
                
                # Get translation for selected language
                if language_code in translations:
                    translation_mapping[object_id] = translations[language_code]
                
                # Fallback to English if available
                if 'en' in translations:
                    fallback_mapping[object_id] = translations['en']
                    
            except (json.JSONDecodeError, KeyError):
                continue
        
        # Cache results
        _translation_cache[cache_key] = translation_mapping
        _translation_cache_fallback[cache_key] = fallback_mapping
        
        return translation_mapping
        
    except Exception:
        return {}

def get_type_name_annotation(language_code=None):
    """
    Get annotation for type_name with translation support
    Dynamically loads translations from database and builds CASE WHEN
    """
    # Lấy language code hiện tại nếu không có
    if not language_code:
        try:
            from core.middleware.refresh_token import get_current_request
            request = get_current_request()
            if request and hasattr(request, 'user') and request.user.is_authenticated:
                if hasattr(request.user, 'language') and request.user.language:
                    language_code = request.user.language.code
        except:
            pass
        if not language_code:
            language_code = 'en'
    
    # 🚀 BATCH LOAD: Load translations once (cached)
    translation_mapping = _load_translations_batch(TerminalType, 'name', language_code)
    cache_key = f"{TerminalType.__name__}.name.{language_code}"
    fallback_mapping = _translation_cache_fallback.get(cache_key, {})
    
    # Build CASE WHEN SQL
    from django.db import connection
    
    # Build CASE WHEN SQL
    from django.db import connection
    
    if connection.vendor == 'postgresql':
        # Build CASE WHEN cho PostgreSQL
        case_conditions = []
        
        # Ưu tiên translation cho language được chọn
        for tt_id, translated_name in translation_mapping.items():
            # Escape single quotes trong translated_name
            escaped_name = translated_name.replace("'", "''")
            case_conditions.append(f"WHEN tt.id = {tt_id} THEN '{escaped_name}'")
        
        # Fallback cho các ID không có translation
        for tt_id, fallback_name in fallback_mapping.items():
            if tt_id not in translation_mapping:
                escaped_name = fallback_name.replace("'", "''")
                case_conditions.append(f"WHEN tt.id = {tt_id} THEN '{escaped_name}'")
        
        if case_conditions:
            case_sql = "CASE " + " ".join(case_conditions) + " ELSE tt.name END"
        else:
            case_sql = "tt.name"
        
        sql = f"""
        SELECT STRING_AGG(
            {case_sql}, ', ' ORDER BY tt.name
        )
        FROM terminals_terminaltype tt
        WHERE tt.id IN (
            SELECT ttt.terminaltype_id 
            FROM terminals_terminal_terminal_types ttt 
            WHERE ttt.terminal_id = terminals_terminal.id
        )
        """
    else:
        # MySQL/SQLite fallback
        case_conditions = []
        
        for tt_id, translated_name in translation_mapping.items():
            escaped_name = translated_name.replace("'", "''")
            case_conditions.append(f"WHEN tt.id = {tt_id} THEN '{escaped_name}'")
        
        for tt_id, fallback_name in fallback_mapping.items():
            if tt_id not in translation_mapping:
                escaped_name = fallback_name.replace("'", "''")
                case_conditions.append(f"WHEN tt.id = {tt_id} THEN '{escaped_name}'")
        
        if case_conditions:
            case_sql = "CASE " + " ".join(case_conditions) + " ELSE tt.name END"
        else:
            case_sql = "tt.name"
        
        sql = f"""
        SELECT GROUP_CONCAT(
            {case_sql} SEPARATOR ', '
        )
        FROM terminals_terminaltype tt
        WHERE tt.id IN (
            SELECT ttt.terminaltype_id 
            FROM terminals_terminal_terminal_types ttt 
            WHERE ttt.terminal_id = terminals_terminal.id
        )
        """
    
    from django.db.models.expressions import RawSQL
    from django.db.models import CharField
    return RawSQL(sql, [], output_field=CharField())

def get_linked_delivery_hubs_annotation():
    """
    Get annotation for linked delivery hub terminals in same routes
    Returns comma-separated names of DELIVERY_HUB terminals in the same routes
    """
    from django.db import connection
    
    
    sql = """
    SELECT STRING_AGG(DISTINCT linked_terminal.name, ', ' ORDER BY linked_terminal.name)
    FROM terminals_terminal linked_terminal
    INNER JOIN terminals_terminal_terminal_types linked_ttt 
        ON linked_terminal.id = linked_ttt.terminal_id
    INNER JOIN terminals_terminaltype linked_tt 
        ON linked_ttt.terminaltype_id = linked_tt.id
    INNER JOIN terminals_routeterminal linked_rt 
        ON linked_terminal.id = linked_rt.terminal_id
    WHERE linked_tt.code = 'DELIVERY_HUB'
    AND linked_rt.route_id IN (
        SELECT rt.route_id
        FROM terminals_routeterminal rt
        WHERE rt.terminal_id = terminals_terminal.id
    )
    AND linked_terminal.id != terminals_terminal.id
    AND linked_terminal.active = true
    """
    
    
    from django.db.models.expressions import RawSQL
    from django.db.models import CharField
    return RawSQL(sql, [], output_field=CharField())

def get_function_names_annotation(language_code=None,type_code=None):
    """
    Get annotation for function_names with translation support
    🚀 OPTIMIZED: Uses batch-loaded cached translations
    Returns comma-separated translated function names
    """
    # Lấy language code hiện tại nếu không có
    if not language_code:
        try:
            from core.middleware.refresh_token import get_current_request
            request = get_current_request()
            if request and hasattr(request, 'user') and request.user.is_authenticated:
                if hasattr(request.user, 'language') and request.user.language:
                    language_code = request.user.language.code
        except:
            pass
        if not language_code:
            language_code = 'en'
    
    # 🚀 BATCH LOAD: Load translations once (cached)
    translation_mapping = _load_translations_batch(Function, 'name', language_code)
    cache_key = f"{Function.__name__}.name.{language_code}"
    fallback_mapping = _translation_cache_fallback.get(cache_key, {})
    
    # Build CASE WHEN SQL
    from django.db import connection
    
    # Build CASE WHEN SQL
    from django.db import connection
    
    if connection.vendor == 'postgresql':
        # Build CASE WHEN cho PostgreSQL
        case_conditions = []
        
        # Ưu tiên translation cho language được chọn
        for func_id, translated_name in translation_mapping.items():
            # Escape single quotes trong translated_name
            escaped_name = translated_name.replace("'", "''")
            case_conditions.append(f"WHEN f.id = {func_id} THEN '{escaped_name}'")
        
        # Fallback cho các ID không có translation
        for func_id, fallback_name in fallback_mapping.items():
            if func_id not in translation_mapping:
                escaped_name = fallback_name.replace("'", "''")
                case_conditions.append(f"WHEN f.id = {func_id} THEN '{escaped_name}'")
        
        if case_conditions:
            case_sql = "CASE " + " ".join(case_conditions) + " ELSE f.name END"
        else:
            case_sql = "f.name"
        if not type_code:
            sql = f"""
            SELECT STRING_AGG(
                {case_sql}, ', ' ORDER BY f.name
            )
            FROM terminals_function f
            WHERE f.id IN (
                SELECT tf.function_id 
                FROM terminals_terminal_functions tf 
                WHERE tf.terminal_id = terminals_terminal.id
            )
            """
        else:
            sql = f"""
            SELECT STRING_AGG(
                {case_sql}, ', ' ORDER BY f.name
            )
            FROM terminals_function f
            WHERE f.id IN (
                SELECT tf.function_id 
                FROM terminals_terminal_functions tf 
                WHERE tf.terminal_id = terminals_terminal.id
                AND f.function_type = '{type_code}'
            )
            """
    else:
        # MySQL/SQLite fallback
        case_conditions = []
        
        for func_id, translated_name in translation_mapping.items():
            escaped_name = translated_name.replace("'", "''")
            case_conditions.append(f"WHEN f.id = {func_id} THEN '{escaped_name}'")
        
        for func_id, fallback_name in fallback_mapping.items():
            if func_id not in translation_mapping:
                escaped_name = fallback_name.replace("'", "''")
                case_conditions.append(f"WHEN f.id = {func_id} THEN '{escaped_name}'")
        
        if case_conditions:
            case_sql = "CASE " + " ".join(case_conditions) + " ELSE f.name END"
        else:
            case_sql = "f.name"
        if not type_code:
            sql = f"""
            SELECT GROUP_CONCAT(
                {case_sql} SEPARATOR ', '
            )
            FROM terminals_function f
            WHERE f.id IN (
                SELECT tf.function_id 
                FROM terminals_terminal_functions tf 
                WHERE tf.terminal_id = terminals_terminal.id
                )
                """
        else:
            sql = f"""
            SELECT GROUP_CONCAT(
                {case_sql} SEPARATOR ', '
            )
            FROM terminals_function f
            WHERE f.id IN (
                SELECT tf.function_id 
                FROM terminals_terminal_functions tf 
                WHERE tf.terminal_id = terminals_terminal.id
                AND f.function_type = '{type_code}'
            )
            """
    from django.db.models.expressions import RawSQL
    from django.db.models import CharField
    return RawSQL(sql, [], output_field=CharField())

class TerminalService:
    """Helper method để convert schema objects to dicts"""
    @staticmethod
    def _convert_schema_to_dict_list(data_list, terminal_id: int) -> List[dict]:
        """Convert list of schema objects to list of dicts"""
        result = []
        for item in data_list:
            if hasattr(item, 'dict'):
                item_dict = item.dict()
            else:
                item_dict = item
            item_dict['terminal_id'] = terminal_id
            result.append(item_dict)
        return result
    @transaction.atomic
    def create_terminal(self, data, avatar, request):
        from terminals.services import OperatingTimeService, ExceptionService
        """
        Create a new terminal
        
        Args:
            data: TerminalCreateSchema data
            
        Returns:
            tuple: (success, result)
        """
        try:
            terminal_data = data.copy()
            terminal_type_ids = terminal_data.pop('terminal_type_ids', None)
            function_ids = terminal_data.pop('function_ids', None)
            group_id = terminal_data.get('group_id', None)
            operating_times_data = terminal_data.pop('operating_times', None)
            exceptions_data = terminal_data.pop('exceptions', None)
            terminal = Terminal()
            group = UserGroup.objects.get(id=group_id) if group_id else None
            
            # Set basic fields
            for key, value in terminal_data.items():
                if hasattr(terminal, key):
                    setattr(terminal, key, value)
            
            terminal.save()
            
            # Handle many-to-many terminal_types
            if terminal_type_ids:
                terminal_types = TerminalType.objects.filter(id__in=terminal_type_ids)
                terminal.terminal_types.set(terminal_types)
                
                # Generate code based on first terminal type for backward compatibility
                first_terminal_type = terminal_types.first()
                if first_terminal_type and data.get('code', None) is None:
                    if first_terminal_type.code == 'DELIVERY_HUB':
                        terminal.code = f"{group.code if group else ''}_spot_{str(terminal.id).zfill(6)}"
                    else:
                        terminal.code = f"{str(terminal.id).zfill(6)}"
                    terminal.save()
                elif data.get('code', None) is not None:
                    terminal.code = data.get('code')
                    terminal.save()
            # Handle many-to-many functions
            if function_ids:
                functions = Function.objects.filter(id__in=function_ids)
                terminal.functions.set(functions)
                terminal.save()
            # Handle measurements
            measurement_fields = ['time_stops', 'weight', 'temperature_range']
            for field in measurement_fields:
                if field in terminal_data and terminal_data[field]:
                    terminal.set_measurement(field, terminal_data[field])
                else:
                    terminal.measurements.filter(measurement_type=field).delete()
           
            # Handle avatar
            if avatar:
                media_file = FileHelper.user_upload_s3(request.user, avatar)
                if media_file:
                    terminal.avatar = media_file
                    terminal.save()
            
            # Handle operating times
            
            if operating_times_data:
                operating_times_list = TerminalService._convert_schema_to_dict_list(operating_times_data, terminal.id)
                success, result = OperatingTimeService.smart_sync(terminal.id, operating_times_list)
                if not success:
                    return False, f"Error creating operating times: {result}"
            
            # Handle exceptions
            
            if exceptions_data:
                exceptions_list = TerminalService._convert_schema_to_dict_list(exceptions_data, terminal.id)
                success, result = ExceptionService.smart_sync(terminal.id, exceptions_list)
                if not success:
                    return False, f"Error creating exceptions: {result}"
            
            return True, terminal
        except ValidationError as e:
            return False, str(e)
        except Exception as e:
            return False, str(e)
    
    @transaction.atomic
    def update_terminal(self, terminal_id, data, avatar=None, request=None):
        from terminals.services import OperatingTimeService, ExceptionService
        """
        Update an existing terminal
        
        Args:
            terminal_id: Terminal ID
            data: TerminalUpdateSchema data
            
        Returns:
            tuple: (success, result)
        """
        try:
            terminal = Terminal.objects.get(id=terminal_id)
            terminal_data = data.copy()
            
            # Pop các field đặc biệt trước để tránh conflict khi loop
            terminal_type_ids = terminal_data.pop('terminal_type_ids', None)
            function_ids = terminal_data.pop('function_ids', None)
            delete_avatar = terminal_data.pop('delete_avatar', False)
            operating_times_data = terminal_data.pop('operating_times', None)
            exceptions_data = terminal_data.pop('exceptions', None)
            
            # Update basic fields
            for key, value in terminal_data.items():
                if hasattr(terminal, key):
                    setattr(terminal, key, value)
            
            # Handle delete_avatar
            if delete_avatar:
                terminal.avatar = None
            
            terminal.save()
            
            # Handle many-to-many terminal_types
            if terminal_type_ids is not None:
                terminal_types = TerminalType.objects.filter(id__in=terminal_type_ids)
                terminal.terminal_types.clear()
                terminal.terminal_types.set(terminal_types)

            # Handle many-to-many functions
            if function_ids is not None:
                functions = Function.objects.filter(id__in=function_ids)
                terminal.functions.clear()
                terminal.functions.set(functions)

            # Handle measurements
            measurement_fields = ['time_stops', 'weight', 'temperature_range']
            for field in measurement_fields:
                if field in terminal_data and terminal_data[field]:
                    terminal.set_measurement(field, terminal_data[field])
                else:
                    terminal.measurements.filter(measurement_type=field).delete()
           
            # Handle avatar upload
            if avatar:
                media_file = FileHelper.user_upload_s3(request.user, avatar)
                if media_file:
                    terminal.avatar = media_file
                    terminal.save()
            
            # Handle operating times - chỉ xử lý khi có truyền vào
            # Logic: Smart sync - chỉ UPDATE/CREATE/DELETE những gì thay đổi
            if operating_times_data is not None:
                operating_times_list = TerminalService._convert_schema_to_dict_list(operating_times_data, terminal.id)
                success, result = OperatingTimeService.smart_sync(terminal.id, operating_times_list)
                if not success:
                    return False, f"Error updating operating times: {result}"
            
            # Handle exceptions - chỉ xử lý khi có truyền vào
            # Logic: Smart sync - chỉ UPDATE/CREATE/DELETE những gì thay đổi
            if exceptions_data is not None:
                exceptions_list = TerminalService._convert_schema_to_dict_list(exceptions_data, terminal.id)
                success, result = ExceptionService.smart_sync(terminal.id, exceptions_list)
                if not success:
                    return False, f"Error updating exceptions: {result}"
            
            return True, terminal
        except ValidationError as e:
            return False, str(e)
        except Exception as e:
            return False, str(e)

    def get_terminal(self, terminal_id):
        """
        Get single terminal by ID
        """
        try:
            return Terminal.objects.prefetch_related(
                'terminal_types', 'functions', 'location_type',
                'operating_times__day_of_week', 'exceptions'
            ).filter(id=terminal_id)
        except Terminal.DoesNotExist:
            return None

    def get_terminals_by_route(self):
        """
        Get all terminals that are in routes
        """
        terminals = Terminal.objects.prefetch_related(
            'terminal_types', 'functions', 'location_type'
        ).filter(
            route_terminals__isnull=False,
            terminal_types__code__in=['DOCKING_STATION']
        ).annotate(
            full_address=Case(
                When(
                    city_province__isnull=False,
                    city_county_district__isnull=False,
                    ward_town_township__isnull=False,
                    street_address__isnull=False,
                    then=Concat(
                        F('city_province'),
                        Value(' '),
                        F('city_county_district'),
                        Value(' '),
                        F('ward_town_township'),
                        Value(' '),
                        F('street_address'),
                        output_field=CharField()
                    )
                ),
                When(
                    city_province__isnull=False,
                    city_county_district__isnull=False,
                    street_address__isnull=False,
                    then=Concat(
                        F('city_province'),
                        Value(' '),
                        F('city_county_district'),
                        Value(' '),
                        F('street_address'),
                        output_field=CharField()
                    )
                ),
                When(
                    city_province__isnull=False,
                    city_county_district__isnull=False,
                    then=Concat(
                        F('city_province'),
                        Value(' '),
                        F('city_county_district'),
                        output_field=CharField()
                    )
                ),
                When(
                    city_province__isnull=False,
                    then=F('city_province')
                ),
                default=Value(''),
                output_field=CharField()
            ),
            organization=F('created_by__userprofilelink__group__code'),
            related_routes_count=Count('route_terminals__route', distinct=True),
            type_name=get_type_name_annotation(),
            function=get_function_names_annotation(),
            linked_terminal=get_linked_delivery_hubs_annotation(),
            avatar__file_url=F('avatar__file_url'),
        ).distinct().order_by('-id')
        
        return terminals

    @transaction.atomic
    def delete_terminals(self, ids):
        """
        Delete multiple terminals
        """
        try:
            ids_list = [int(id.strip()) for id in ids.split(',')]
            Terminal.objects.filter(id__in=ids_list).delete()
            return True, None
        except Exception as e:
            return False, str(e)

    @transaction.atomic
    def change_status(self, ids):
        """
        Change status of terminals
        """
        try:
            ids_list = [int(id.strip()) for id in ids.split(',')]
            for terminal_id in ids_list:
                terminal = Terminal.objects.get(id=terminal_id)
                terminal.active = not terminal.active
                terminal.save()
            return True, None
        except Exception as e:
            return False, str(e)

    def get_docking_station_terminals(self, query_params=None, user_units=None, search_route=False):
        """
        Get all docking station terminals with optional filtering
        """
        terminals = Terminal.objects.prefetch_related(
            'terminal_types', 'functions', 'location_type'
        ).filter(
            terminal_types__code='DOCKING_STATION',
        ).annotate(
            address=Concat(
                Coalesce(F('city_province'), Value(''), output_field=CharField()),
                Value(', '),
                Coalesce(F('city_county_district'), Value(''), output_field=CharField()),
                Value(', '),
                Coalesce(F('ward_town_township'), Value(''), output_field=CharField()),
                Value(', '),
                Coalesce(F('street_address'), Value(''), output_field=CharField()),
                output_field=CharField()
            ),
            organization=F('created_by__userprofilelink__group__code'),
            related_routes_count=Count('route_terminals__route', distinct=True),
            type_name=get_type_name_annotation(),
            function=get_function_names_annotation(type_code='docking_station'),
            linked_terminal=get_linked_delivery_hubs_annotation(),
            purpose_type__name = F('purpose_type__name'),
            terminal_purpose__name = F('terminal_purpose__name'),
            avatar__file_url=F('avatar__file_url'),
        ).distinct().order_by('-id')
        
        if query_params:
            # Apply any filters based on query_params
            pass
        if not search_route:
            terminals = terminals.exclude(
                terminal_types__code='DELIVERY_HUB'
            )
        
        return terminals

    def get_infrastructure_terminals(self, query_params=None, user_units=None):
        """
        Get all infrastructure terminals with optional filtering
        """
        terminals = Terminal.objects.prefetch_related(
            'terminal_types', 'functions', 'location_type'
        ).filter(
            functions__function_type='infrastructure'
        ).annotate(
            address=Concat(
                Coalesce(F('city_province'), Value(''), output_field=CharField()),
                Value(', '),
                Coalesce(F('city_county_district'), Value(''), output_field=CharField()),
                Value(', '),
                Coalesce(F('ward_town_township'), Value(''), output_field=CharField()),
                Value(', '),
                Coalesce(F('street_address'), Value(''), output_field=CharField()),
                output_field=CharField()
            ),
            organization=F('created_by__userprofilelink__group__code'),
            related_routes_count=Count('route_terminals__route', distinct=True),
            type_name=get_type_name_annotation(),
            function=get_function_names_annotation(type_code='infrastructure'),
            linked_terminal=get_linked_delivery_hubs_annotation(),
            purpose_type__name = F('purpose_type__name'),
            terminal_purpose__name = F('terminal_purpose__name'),
            avatar__file_url=F('avatar__file_url'),
        ).distinct().order_by('-id')
        
        if query_params:
            # Apply any filters based on query_params
            pass
        
        return terminals

    def get_regular_terminals(self, query_params=None, user_units=None):
        """
        Get all regular terminals excluding specific types
        🚀 OPTIMIZED: Filter M2M first, then distinct, then annotate to avoid expensive DISTINCT on annotated fields
        """
        # 🚀 OPTIMIZED: Filter M2M first and distinct BEFORE annotations to avoid expensive DISTINCT queries
        terminals = Terminal.objects.prefetch_related(
            'terminal_types', 'functions', 'location_type'
        ).exclude(
            terminal_types__code__in=['TEMP']
        ).distinct()  # Distinct BEFORE annotations to avoid expensive DISTINCT on annotated fields
        
        # 🚀 OPTIMIZED: Add annotations AFTER distinct to avoid DISTINCT on complex annotations
        terminals = terminals.annotate(
            address=Concat(
                Coalesce(F('city_province'), Value(''), output_field=CharField()),
                Value(', '),
                Coalesce(F('city_county_district'), Value(''), output_field=CharField()),
                Value(', '),
                Coalesce(F('ward_town_township'), Value(''), output_field=CharField()),
                Value(', '),
                Coalesce(F('street_address'), Value(''), output_field=CharField()),
                output_field=CharField()
            ),
            organization=F('created_by__userprofilelink__group__code'),
            related_routes_count=Count('route_terminals__route', distinct=True),
            type_name=get_type_name_annotation(),
            function=get_function_names_annotation(),
            linked_terminal=get_linked_delivery_hubs_annotation(),
            purpose_type__name = F('purpose_type__name'),
            terminal_purpose__name = F('terminal_purpose__name'),
            avatar__file_url=F('avatar__file_url'),
        ).order_by('-id')
        
        if query_params:
            # Apply any filters based on query_params
            pass
        
        return terminals

    @transaction.atomic
    def _activate_single_terminal(self, terminal, skip_transit_check=False):
        """
        Helper method to activate a single terminal
        When activating a hub, also activate related dockings in the same routes
        
        Args:
            terminal: Terminal instance
            skip_transit_check: Skip transit operation check (for auto activation)
        
        Returns:
            tuple: (success, error_message)
        """
        try:
            # Detect if we're in task context (no request) - use _base_manager
            from core.middleware.refresh_token import get_current_request
            request = get_current_request()
            use_base_manager = request is None or not hasattr(request, 'user') or not request.user.is_authenticated
            
            terminal.active = True
            terminal.deactivate_reason = None
            
            # Check if terminal is a hub
            is_hub = terminal.terminal_types.filter(code='DELIVERY_HUB').exists()
            
            if is_hub:
                # Get all routes containing this hub - use appropriate manager
                routes_manager = Routes._base_manager if use_base_manager else Routes.objects
                hub_routes = routes_manager.filter(
                    route_terminals__terminal=terminal
                ).distinct()
                
                # Get all dockings in the same routes - use appropriate manager
                terminal_manager = Terminal._base_manager if use_base_manager else Terminal.objects
                dockings_in_same_routes = terminal_manager.filter(
                    route_terminals__route__in=hub_routes,
                    terminal_types__code='DOCKING_STATION'
                ).exclude(id=terminal.id).distinct()
                
                # Activate all dockings in the same routes
                for docking in dockings_in_same_routes:
                    docking.active = True
                    docking.save()
            
            terminal.save()
            return True, None
        except Exception as e:
            return False, str(e)

    def activate(self, ids):
        """
        Activate terminals
        When activating a hub, also activate related dockings in the same routes
        """
        try:
            ids_list = [int(id.strip()) for id in ids.split(',')]
            for terminal_id in ids_list:
                terminal = Terminal.objects.get(id=terminal_id)
                success, error = self._activate_single_terminal(terminal)
                if not success:
                    return False, error
            return True, None
        except Exception as e:
            return False, str(e)

    @staticmethod
    def get_terminals_in_transit_operation():
        """
        Get terminals in transit operation
        """
        # Detect if we're in task context (no request) - use _base_manager
        from core.middleware.refresh_token import get_current_request
        request = get_current_request()
        use_base_manager = request is None or not hasattr(request, 'user') or not request.user.is_authenticated
        
        # get all routes in transit operations - use appropriate manager
        delivery_op_manager = DeliveryOperation._base_manager if use_base_manager else DeliveryOperation.objects
        routes_manager = Routes._base_manager if use_base_manager else Routes.objects
        route_terminal_manager = RouteTerminal._base_manager if use_base_manager else RouteTerminal.objects
        terminal_manager = Terminal._base_manager if use_base_manager else Terminal.objects
        
        in_transit_operations = delivery_op_manager.filter(current_status__code="in_transit_processing")
        routes = routes_manager.filter(id__in=in_transit_operations.values_list('route_id', flat=True))
        route_terminals = route_terminal_manager.filter(route__in=routes)
        # get all terminals in routes
        terminals = terminal_manager.filter(id__in=route_terminals.values_list('terminal_id', flat=True))
        return terminals
    
    @transaction.atomic
    def _deactivate_single_terminal(self, terminal, skip_transit_check=False, skip_validation=False, deactivate_reason=None):
        """
        Helper method to deactivate a single terminal
        
        Args:
            terminal: Terminal instance
            skip_transit_check: Skip transit operation check (for auto activation)
            skip_validation: Skip validation checks (for auto activation)
            deactivate_reason: Optional DeactivateReason instance
        
        Returns:
            tuple: (success, error_message)
        """
        try:
            # Detect if we're in task context (no request) - use _base_manager
            from core.middleware.refresh_token import get_current_request
            request = get_current_request()
            use_base_manager = request is None or not hasattr(request, 'user') or not request.user.is_authenticated
            
            # Check transit operation (skip for auto activation)
            if not skip_transit_check:
                terminals_in_transit_operation = self.get_terminals_in_transit_operation()
                if terminal in terminals_in_transit_operation:
                    return False, get_message(MESSAGE_ENUM.DELIVERY_HUB_ON_MISSION)
            
            # Check if terminal is a hub
            is_hub = terminal.terminal_types.filter(code='DELIVERY_HUB').exists()
            
            if is_hub:
                # Get all routes containing this hub - use appropriate manager
                routes_manager = Routes._base_manager if use_base_manager else Routes.objects
                hub_routes = routes_manager.filter(
                    route_terminals__terminal=terminal
                ).distinct()
                hub_route_ids = list(hub_routes.values_list('id', flat=True))
                # Get all dockings in the same routes - use appropriate manager
                terminal_manager = Terminal._base_manager if use_base_manager else Terminal.objects
                dockings_in_same_routes = terminal_manager.filter(
                    route_terminals__route__in=hub_routes,
                    terminal_types__code='DOCKING_STATION'
                ).exclude(id=terminal.id).distinct()
                # Validation: Check if dockings are in routes without the hub (skip for auto activation)
                if not skip_validation:
                    # Collect all routes that contain dockings but not the hub
                    all_routes_without_hub = set()
                    for docking in dockings_in_same_routes:
                        docking_routes = hub_routes.filter(
                            route_terminals__terminal=docking
                        ).distinct()
                        docking_route_ids = set(docking_routes.values_list('id', flat=True))
                        # Find routes that contain docking but not the hub
                        routes_without_hub = docking_route_ids - set(hub_route_ids)
                        all_routes_without_hub.update(routes_without_hub)
                    # If there are any routes without the hub, return error
                    if all_routes_without_hub:
                        route_ids_str = ', '.join(map(str, sorted(all_routes_without_hub)))
                        error_msg = get_message(MESSAGE_ENUM.DEACTIVATE_DELIVERY_HUB_WITH_DOCKING_IN_OTHER_ROUTE).format(
                            hub_name=terminal.name,
                            hub_id=terminal.id,
                            route_ids=route_ids_str
                        )
                        return False, error_msg
                
                # Deactivate all dockings in the same routes
                for docking in dockings_in_same_routes:
                    docking.active = False
                    docking.save()
            
            terminal.active = False
            if deactivate_reason:
                terminal.deactivate_reason = deactivate_reason
            terminal.save()
            return True, None
        except Exception as e:
            return False, str(e)

    def deactivate(self, ids, deactivate_reason_id=None):
        """
        Deactivate terminals
        
        Args:
            ids: Comma-separated string of terminal IDs
            deactivate_reason_id: Optional ID of DeactivateReason
        """
        try:
            ids_list = [int(id.strip()) for id in ids.split(',')]
            deactivate_reason = None
            if deactivate_reason_id:
                try:
                    deactivate_reason = DeactivateReason.objects.get(id=deactivate_reason_id)
                except DeactivateReason.DoesNotExist:
                    return False, f"DeactivateReason with id {deactivate_reason_id} not found"
            
            for terminal_id in ids_list:
                terminal = Terminal.objects.get(id=terminal_id)
                success, error = self._deactivate_single_terminal(
                    terminal, 
                    skip_transit_check=False, 
                    skip_validation=False,
                    deactivate_reason=deactivate_reason
                )
                if not success:
                    return False, error
            return True, None
        except Exception as e:
            return False, str(e)

    @transaction.atomic
    def get_terminals_by_route_etri(self):
        """
        Get docking station terminals for ETRI
        """
        return Terminal.objects.filter(
            active=True,
            terminal_types__code='DOCKING_STATION'
        ).prefetch_related('terminal_types').distinct().annotate(
            full_address=Concat(
                Coalesce(F('name'), Value(''), output_field=CharField()),
                Value('('),
                Coalesce(F('city_province'), Value(''), output_field=CharField()),
                Value(', '),
                Coalesce(F('city_county_district'), Value(''), output_field=CharField()),
                Value(', '),
                Coalesce(F('ward_town_township'), Value(''), output_field=CharField()),
                Value(', '),
                Coalesce(F('street_address'), Value(''), output_field=CharField()),
                Value(')'),
                output_field=CharField()
            ),
            type_name=get_type_name_annotation(),
            purpose_type__name = F('purpose_type__name'),
            terminal_purpose__name = F('terminal_purpose__name')
        ).order_by('-id')
    
class TerminalTypeService:
    @transaction.atomic
    def create_terminal_type(self, data):
        """
        Create a new terminal type
        
        Args:
            data: TerminalTypeInSchema data
            
        Returns:
            tuple: (success, result)
        """
        try:
            terminal_type_data = data.dict()
            
            # Create the terminal type
            terminal_type = TerminalType.objects.create(**terminal_type_data)
            
            return True, terminal_type
        except ValidationError as e:
            return False, str(e)
        except Exception as e:
            return False, str(e)
    
    def get_terminal_type_by_code(self, code):
        """
        Get terminal type by code
        
        Args:
            code: TerminalType code
            
        Returns:
            TerminalType or None
        """
        try:
            return TerminalType.objects.get(code=code)
        except TerminalType.DoesNotExist:
            return None
    
    @transaction.atomic
    def update_terminal_type(self, terminal_type_id, data):
        """
        Update an existing terminal type
        
        Args:
            terminal_type_id: TerminalType ID
            data: TerminalTypeInSchema data
            
        Returns:
            tuple: (success, result)
        """
        try:
            # Get terminal type
            try:
                terminal_type = TerminalType.objects.get(id=terminal_type_id)
            except TerminalType.DoesNotExist:
                return False, "Terminal type not found"
            
            # Update terminal type fields
            terminal_type_data = {k: v for k, v in data.dict().items() if v is not None}
            for field, value in terminal_type_data.items():
                setattr(terminal_type, field, value)
            
            terminal_type.save()
            
            return True, terminal_type
        except ValidationError as e:
            return False, str(e)
        except Exception as e:
            return False, str(e)
    
    def get_terminal_type(self, terminal_type_id):
        """
        Get terminal type by ID
        
        Args:
            terminal_type_id: TerminalType ID
            
        Returns:
            TerminalType or None
        """
        try:
            return TerminalType.objects.get(id=terminal_type_id)
        except TerminalType.DoesNotExist:
            return None
    
    def get_terminal_types(self):
        """
        Get all terminal types
        
        Returns:
            QuerySet: TerminalType queryset
        """
        return TerminalType.objects.all()
    
    @transaction.atomic
    def delete_terminal_type(self, terminal_type_id):
        """
        Delete a terminal type
        
        Args:
            terminal_type_id: TerminalType ID
            
        Returns:
            tuple: (success, result)
        """
        try:
            terminal_type = TerminalType.objects.get(id=terminal_type_id)
            terminal_type.delete()
            return True, get_message(MESSAGE_ENUM.ACTION_DELETE_SUCCESS)
        except TerminalType.DoesNotExist:
            return False, "Terminal type not found"
        except Exception as e:
            return False, str(e) 
        
class LocationTypeService:
    def get_location_types(self):
        return LocationType.objects.all()
    
class DeliveryHubService:
    def get_delivery_hubs(self):
        return Terminal.objects.filter(
            terminal_types__code='DELIVERY_HUB'
        ).prefetch_related('terminal_types').distinct().annotate(
            type_name=get_type_name_annotation(),
            function=get_function_names_annotation(type_code='delivery_hub'),
            avatar__file_url=F('avatar__file_url'),
        ).order_by('-id')
    
    def get_delivery_hub(self, id):
        return Terminal.objects.filter(id=id).prefetch_related('terminal_types').annotate(
            type_name=get_type_name_annotation(),
            function=get_function_names_annotation(type_code='delivery_hub'),
            avatar__file_url=F('avatar__file_url'),
        ).first()
    
    @transaction.atomic
    def create_delivery_hub(self, data, avatar, request):
        try:
            from terminals.services import OperatingTimeService, ExceptionService
            terminal_data = data.copy()
            function_ids = terminal_data.pop('function_ids', None)
            delivery_hub_types = TerminalType.objects.filter(id__in=terminal_data.get('terminal_type_ids', None))
            operating_times_data = terminal_data.pop('operating_times', None)
            exceptions_data = terminal_data.pop('exceptions', None)
            terminal = Terminal()
            group = request.user.userprofilelink.group if request.user.userprofilelink else None
            
            # Set basic fields
            for key, value in terminal_data.items():
                if hasattr(terminal, key):
                    setattr(terminal, key, value)
            
            terminal.save()
            
            # Set delivery hub types
            terminal.terminal_types.set(delivery_hub_types)
            if data.get('code', None) is None:
                terminal.code = f"{group.code if group else ''}_spot_{str(terminal.id).zfill(6)}"
            elif data.get('code', None) is not None:
                terminal.code = data.get('code')
                terminal.save()
            terminal.save()
            # Handle many-to-many functions
            if function_ids:
                functions = Function.objects.filter(id__in=function_ids)
                terminal.functions.clear()
                terminal.functions.set(functions)
                terminal.save()
            if operating_times_data:
                operating_times_list = TerminalService._convert_schema_to_dict_list(operating_times_data, terminal.id)
                success, result = OperatingTimeService.smart_sync(terminal.id, operating_times_list)
                if not success:
                    return False, f"Error creating operating times: {result}"
            
            # Handle exceptions
            
            if exceptions_data:
                exceptions_list = TerminalService._convert_schema_to_dict_list(exceptions_data, terminal.id)
                success, result = ExceptionService.smart_sync(terminal.id, exceptions_list)
                if not success:
                    return False, f"Error creating exceptions: {result}"
            # Handle measurements
            measurement_fields = ['time_stops', 'weight', 'temperature_range']
            for field in measurement_fields:
                if field in terminal_data and terminal_data[field]:
                    terminal.set_measurement(field, terminal_data[field])
                else:
                    terminal.measurements.filter(measurement_type=field).delete()
           
            # Handle avatar
            if avatar:
                media_file = FileHelper.user_upload_s3(request.user, avatar)
                if media_file:
                    terminal.avatar = media_file
                    terminal.save()
            
            return True, terminal
        except ValidationError as e:
            return False, str(e)
        except Exception as e:
            return False, str(e)
    
class DockingStationService:
    def get_docking_stations(self):
        return Terminal.objects.filter(
            terminal_types__code='DOCKING_STATION'
        ).prefetch_related('terminal_types').distinct().annotate(
            type_name=get_type_name_annotation(),
            function=get_function_names_annotation(type_code='docking_station')
        )
    
    def get_docking_station(self, id):
        return Terminal.objects.filter(id=id).prefetch_related('terminal_types').annotate(
            type_name=get_type_name_annotation(),
            function=get_function_names_annotation(type_code='docking_station')
        ).first()
