from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple, Type, TypeVar, Union, get_type_hints, ClassVar
from pydantic import BaseModel, create_model
from django.db import models
from django.db.models import Model, QuerySet, Prefetch
from django.contrib.contenttypes.models import ContentType
from core.common.schema_utils import DynamicSchema

if TYPE_CHECKING:
    from devices.models import Measurement

class MeasurableDynamicSchema(DynamicSchema):
    """
    Extension of DynamicSchema that automatically handles measurement fields 
    from models with MEASUREMENT_TYPES or that inherit from MeasurableModel.
    Optimized for performance with bulk measurement loading.
    """
    
    _MEASUREMENT_PLAN_CACHE: ClassVar[Dict[Tuple[Type[Model], Tuple[str, ...], bool, bool], List[Dict[str, Any]]]] = {}
    _MEASUREMENT_FORMATTERS: ClassVar[Dict[Tuple[str, bool, bool], Callable[['Measurement'], Any]]] = {}
    # 🚀 PERFORMANCE: Cache ContentType lookups to avoid repeated queries
    _CONTENT_TYPE_CACHE: ClassVar[Dict[Type[Model], 'ContentType']] = {}
    
    @classmethod
    def _normalize_measurement_types(cls, measurement_types, model_class: Type[Model]) -> List[str]:
        if measurement_types:
            if isinstance(measurement_types, dict):
                return list(measurement_types.keys())
            if isinstance(measurement_types, (list, tuple, set)):
                return list(measurement_types)
            return [str(measurement_types)]
        
        model_measurements = getattr(model_class, 'MEASUREMENT_TYPES', {})
        if isinstance(model_measurements, dict):
            return list(model_measurements.keys())
        if isinstance(model_measurements, (list, tuple, set)):
            return list(model_measurements)
        return []
    
    @classmethod
    def _is_model_field(cls, model_class: Type[Model], field_name: str) -> bool:
        """
        ⚠️ CONFLICT DETECTION: Kiểm tra xem field_name có phải là field của model không.
        Dùng để phân biệt giữa field của model và measurement_type.
        """
        try:
            from django.core.exceptions import FieldDoesNotExist
            model_class._meta.get_field(field_name)
            return True
        except (FieldDoesNotExist, AttributeError):
            return False
    
    @classmethod
    def _get_measurement_plan(cls, model_class: Type[Model], measurement_types: List[str], raw_measurements: bool, many: bool) -> List[Dict[str, Any]]:
        """
        🚀 PERFORMANCE: Plan now only contains metadata, not formatters.
        Formatters are created in _collect_measurements_in_batch with user_units and model_class passed in.
        This allows caching the plan while still supporting per-request user_units.
        """
        types_tuple = tuple(sorted(measurement_types or []))
        cache_key = (model_class, types_tuple, raw_measurements, many)
        if cache_key in cls._MEASUREMENT_PLAN_CACHE:
            return cls._MEASUREMENT_PLAN_CACHE[cache_key]
        
        plan: List[Dict[str, Any]] = []
        model_measurements = getattr(model_class, 'MEASUREMENT_TYPES', {})
        
        # ⚠️ CONFLICT DETECTION: Kiểm tra và cảnh báo nếu measurement_type trùng với field của model
        import logging
        logger = logging.getLogger(__name__)
        
        for measurement_type in measurement_types:
            config = model_measurements.get(measurement_type, {}) if isinstance(model_measurements, dict) else {}
            data_type = config.get('type', 'simple')
            
            # ⚠️ CONFLICT DETECTION: Kiểm tra xung đột với field của model
            if cls._is_model_field(model_class, measurement_type):
                logger.warning(
                    f"[MeasurableDynamicSchema] ⚠️ CONFLICT: Measurement type '{measurement_type}' "
                    f"conflicts with model field '{measurement_type}' in {model_class.__name__}. "
                    f"Measurement will be skipped if model field has value. "
                    f"Consider renaming measurement_type to avoid conflict."
                )
            
            # 🚀 PERFORMANCE: Don't create formatter here - it will be created in _collect_measurements_in_batch
            # with user_units and model_class passed in to avoid N+1 AdminConfig and entity queries
            plan.append({
                'measurement_type': measurement_type,
                'data_type': data_type,
                'raw_measurements': raw_measurements,
                'output_key': measurement_type,
            })
        
        cls._MEASUREMENT_PLAN_CACHE[cache_key] = plan
        return plan
    
    @classmethod
    def _get_user_units_once(cls) -> dict:
        """
        🚀 PERFORMANCE: Fetch AdminConfig user_units ONCE at the start.
        This is called once per batch, not per measurement.
        """
        from devices.utils import get_cached_admin_config
        config = get_cached_admin_config()
        if config:
            return config.get('unit_preferences', {})
        return {}
    
    @classmethod
    def _get_measurement_formatter(cls, data_type: str, raw_measurements: bool, many: bool, user_units: dict = None, model_class: Type[Model] = None) -> Callable[['Measurement'], Any]:
        """
        🚀 PERFORMANCE: Formatter now accepts user_units and model_class to avoid:
        1. Repeated AdminConfig queries (user_units passed once)
        2. N+1 queries for measurement.entity (model_class passed instead)
        """
        # Note: We don't cache formatters with user_units/model_class since they can vary per request
        # But that's fine - creating a simple closure is fast
        
        if raw_measurements:
            def formatter(measurement: 'Measurement') -> Any:
                if measurement is None:
                    return None
                from devices.utils import convert_measurement_data_to_user_units
                return convert_measurement_data_to_user_units(measurement, user_units, model_class)
        else:
            def formatter(measurement: 'Measurement') -> Any:
                if measurement is None:
                    return None
                from devices.utils import get_formatted_measurement
                return get_formatted_measurement(measurement, user_units, model_class)
        
        return formatter
    
    @classmethod
    def _get_cached_content_type(cls, model_class: Type[Model]) -> 'ContentType':
        """
        🚀 PERFORMANCE: Get ContentType with caching to avoid repeated queries.
        ContentType is immutable so safe to cache indefinitely.
        """
        if model_class in cls._CONTENT_TYPE_CACHE:
            return cls._CONTENT_TYPE_CACHE[model_class]
        
        content_type = ContentType.objects.get_for_model(model_class)
        cls._CONTENT_TYPE_CACHE[model_class] = content_type
        return content_type
    
    @classmethod
    def _prefetch_measurement_entities(cls, measurements: List['Measurement'], model_class: Type[Model]) -> Dict[int, Model]:
        """
        🚀 PERFORMANCE: Prefetch entities for measurements to avoid N+1 queries when accessing measurement.entity.
        
        Since GenericForeignKey doesn't support prefetch_related directly, we manually fetch all entities
        in one query and cache them. This prevents N+1 queries when formatters access measurement.entity
        as a fallback (though model_class should be used primarily).
        
        Args:
            measurements: List of Measurement objects
            model_class: The model class that these measurements belong to
            
        Returns:
            Dict mapping object_id -> entity instance
        """
        if not measurements:
            return {}
        
        # Extract unique object_ids
        object_ids = list(set(m.object_id for m in measurements if m.object_id))
        if not object_ids:
            return {}
        
        # Fetch all entities in ONE query using in_bulk for efficiency
        entities = model_class.objects.filter(id__in=object_ids).in_bulk(object_ids)
        
        # Cache entities in measurements to avoid future queries
        # Note: GenericForeignKey will still query if accessed directly, but this helps
        # when formatters need to access measurement.entity as fallback
        entity_map = {}
        for measurement in measurements:
            if measurement.object_id in entities:
                entity = entities[measurement.object_id]
                # Cache entity to avoid future queries
                # This is used as fallback when model_class doesn't have MEASUREMENT_TYPES
                measurement._cached_entity = entity
                entity_map[measurement.object_id] = entity
        
        return entity_map
    
    @classmethod
    def _collect_measurements_in_batch(cls, instances: List[Model], plan: List[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
        """
        🚀 ADAPTIVE PERFORMANCE: Chooses optimal strategy based on batch size.
        - Small batches (< 50 records): Single-pass format (low overhead)
        - Large batches (>= 50 records): Batch processing with grouping (CPU cache friendly)
        """
        if not instances or not plan:
            return {}
        
        plan_types = {entry['measurement_type'] for entry in plan}
        if not plan_types:
            return {}
        
        # 🚀 PERFORMANCE: Fetch user_units ONCE for entire batch (not per measurement!)
        user_units = cls._get_user_units_once()
        
        # 🚀 PERFORMANCE: Get model_class ONCE (all instances are same type in batch)
        model_class = instances[0].__class__
        
        # 🚀 PERFORMANCE: Cache MEASUREMENT_TYPES to avoid repeated getattr
        model_measurement_types = getattr(model_class, 'MEASUREMENT_TYPES', None)
        
        # ⚠️ N+1 PREVENTION: Validate model_class has MEASUREMENT_TYPES to avoid fallback to measurement.entity
        if not model_measurement_types:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                f"[MeasurableDynamicSchema] ⚠️ N+1 RISK: {model_class.__name__} does not have MEASUREMENT_TYPES. "
                f"Fallback to measurement.entity may cause N+1 queries."
            )
        
        # 🚀 PERFORMANCE: Create formatters with user_units and model_class already included
        # This avoids:
        # 1. AdminConfig query inside each measurement.get_formatted_value()
        # 2. N+1 query for measurement.entity (use model_class instead)
        formatter_lookup = {}
        for entry in plan:
            data_type = entry.get('data_type', 'simple')
            raw_measurements = entry.get('raw_measurements', False)
            formatter_lookup[entry['measurement_type']] = cls._get_measurement_formatter(
                data_type, raw_measurements, many=True, user_units=user_units, model_class=model_class
            )
        
        # 🚀 ADAPTIVE: Choose strategy based on batch size
        BATCH_SIZE_THRESHOLD = 50  # Tune this based on profiling
        use_batch_processing = len(instances) >= BATCH_SIZE_THRESHOLD
        
        if use_batch_processing:
            # Strategy 2: Large batch - Collect then group then format (CPU cache friendly)
            return cls._collect_measurements_large_batch(instances, plan_types, formatter_lookup, model_class)
        else:
            # Strategy 1: Small batch - Single-pass format (low overhead)
            return cls._collect_measurements_small_batch(instances, plan_types, formatter_lookup, model_class)
    
    @classmethod
    def _collect_measurements_small_batch(cls, instances: List[Model], plan_types: set, 
                                          formatter_lookup: Dict[str, Callable], model_class: Type[Model]) -> Dict[int, Dict[str, Any]]:
        """
        Strategy 1: Small batch (< 50 records)
        - Single-pass format: Format immediately while collecting
        - Low memory overhead, optimal for small datasets
        """
        result_map: Dict[int, Dict[str, Any]] = {}
        missing_ids: List[int] = []
        
        # Format immediately while collecting (single pass, no extra memory)
        # 🚀 PERFORMANCE: Use direct attribute access with safe fallback to maintain compatibility
        for instance in instances:
            # ⚠️ SAFETY: Use getattr with fallback to ensure compatibility with all model types
            # Direct access is faster but we need fallback for edge cases
            try:
                instance_id = instance.id
            except AttributeError:
                instance_id = getattr(instance, 'id', None)
            
            if instance_id is None:
                continue
            result_map[instance_id] = {}
            # 🚀 PERFORMANCE: Direct cache access is faster than getattr, but with safe fallback
            # This maintains compatibility with DynamicSchema's prefetch logic
            cache = getattr(instance, '_prefetched_objects_cache', None)
            prefetched = cache.get('measurements') if cache else None
            if prefetched is not None:
                # 🚀 PERFORMANCE: Pre-check formatter_lookup keys to avoid repeated lookups
                for measurement in prefetched:
                    # ⚠️ SAFETY: Use getattr for measurement_type to handle edge cases
                    measurement_type = getattr(measurement, 'measurement_type', None)
                    if measurement_type and measurement_type in formatter_lookup:
                        formatted_value = formatter_lookup[measurement_type](measurement)
                        if formatted_value is not None:
                            result_map[instance_id][measurement_type] = formatted_value
            else:
                missing_ids.append(instance_id)
        
        # Fetch missing measurements in ONE query and format immediately
        if missing_ids:
            from devices.models import Measurement
            content_type = cls._get_cached_content_type(model_class)
            # 🚀 PERFORMANCE: Convert to list immediately to avoid multiple queries
            measurements = list(Measurement.objects.filter(
                content_type=content_type,
                measurement_type__in=plan_types,
                object_id__in=missing_ids
            ).only('id', 'object_id', 'measurement_type', 'data', 'content_type'))
            
            # 🚀 PERFORMANCE: Only prefetch entities if model_class doesn't have MEASUREMENT_TYPES
            # Otherwise, formatters will use model_class directly (faster)
            model_measurement_types = getattr(model_class, 'MEASUREMENT_TYPES', None)
            if not model_measurement_types:
                cls._prefetch_measurement_entities(measurements, model_class)
            
            # 🚀 PERFORMANCE: Batch format all measurements at once
            # ⚠️ SAFETY: Use getattr for safe attribute access to maintain compatibility
            for measurement in measurements:
                measurement_type = getattr(measurement, 'measurement_type', None)
                if not measurement_type or measurement_type not in formatter_lookup:
                    continue
                instance_id = getattr(measurement, 'object_id', None)
                if instance_id is None or instance_id not in result_map:
                    continue
                formatter = formatter_lookup[measurement_type]
                formatted_value = formatter(measurement)
                if formatted_value is not None:
                    result_map[instance_id][measurement_type] = formatted_value
        
        return result_map
    
    @classmethod
    def _collect_measurements_large_batch(cls, instances: List[Model], plan_types: set,
                                         formatter_lookup: Dict[str, Callable], model_class: Type[Model]) -> Dict[int, Dict[str, Any]]:
        """
        Strategy 2: Large batch (>= 50 records)
        - Collect all measurements first
        - Group by measurement_type for CPU cache locality
        - Format in batches by type
        - Optimal for large datasets where CPU cache reuse matters
        """
        result_map: Dict[int, Dict[str, Any]] = {}
        missing_ids: List[int] = []
        
        # Step 1: Collect all measurements first
        measurements_to_format: List[Tuple[int, str, 'Measurement']] = []
        
        # 🚀 PERFORMANCE: Use direct attribute access with safe fallback to maintain compatibility
        for instance in instances:
            # ⚠️ SAFETY: Use getattr with fallback to ensure compatibility with all model types
            # Direct access is faster but we need fallback for edge cases
            try:
                instance_id = instance.id
            except AttributeError:
                instance_id = getattr(instance, 'id', None)
            
            if instance_id is None:
                continue
            result_map[instance_id] = {}
            # 🚀 PERFORMANCE: Direct cache access is faster than getattr, but with safe fallback
            # This maintains compatibility with DynamicSchema's prefetch logic
            cache = getattr(instance, '_prefetched_objects_cache', None)
            prefetched = cache.get('measurements') if cache else None
            if prefetched is not None:
                for measurement in prefetched:
                    # ⚠️ SAFETY: Use getattr for measurement_type to handle edge cases
                    measurement_type = getattr(measurement, 'measurement_type', None)
                    if measurement_type and measurement_type in formatter_lookup:
                        measurements_to_format.append((instance_id, measurement_type, measurement))
            else:
                missing_ids.append(instance_id)
        
        # Step 2: Fetch missing measurements in ONE query
        if missing_ids:
            from devices.models import Measurement
            content_type = cls._get_cached_content_type(model_class)
            # 🚀 PERFORMANCE: Convert to list immediately to avoid multiple queries
            measurements = list(Measurement.objects.filter(
                content_type=content_type,
                measurement_type__in=plan_types,
                object_id__in=missing_ids
            ).only('id', 'object_id', 'measurement_type', 'data', 'content_type'))
            
            # 🚀 PERFORMANCE: Only prefetch entities if model_class doesn't have MEASUREMENT_TYPES
            # Otherwise, formatters will use model_class directly (faster)
            model_measurement_types = getattr(model_class, 'MEASUREMENT_TYPES', None)
            if not model_measurement_types:
                cls._prefetch_measurement_entities(measurements, model_class)
            
            # ⚠️ SAFETY: Use getattr for safe attribute access to maintain compatibility
            for measurement in measurements:
                measurement_type = getattr(measurement, 'measurement_type', None)
                if not measurement_type or measurement_type not in formatter_lookup:
                    continue
                instance_id = getattr(measurement, 'object_id', None)
                if instance_id is None or instance_id not in result_map:
                    continue
                measurements_to_format.append((instance_id, measurement_type, measurement))
        
        # Step 3: Group by measurement_type for CPU cache locality
        measurements_by_type: Dict[str, List[Tuple[int, 'Measurement']]] = {}
        for instance_id, measurement_type, measurement in measurements_to_format:
            if measurement_type not in measurements_by_type:
                measurements_by_type[measurement_type] = []
            measurements_by_type[measurement_type].append((instance_id, measurement))
        
        # Step 4: Format all measurements of the same type together
        # This improves CPU cache hit rate since formatter code is reused
        for measurement_type, measurement_list in measurements_by_type.items():
            formatter = formatter_lookup[measurement_type]
            for instance_id, measurement in measurement_list:
                formatted_value = formatter(measurement)
                if formatted_value is not None:
                    result_map[instance_id][measurement_type] = formatted_value
        
        return result_map
    
    @classmethod
    def _apply_measurement_plan_to_many(cls, instances: List[Model], result_list: List[Dict[str, Any]], plan: List[Dict[str, Any]]) -> None:
        measurement_map = cls._collect_measurements_in_batch(instances, plan)
        if not measurement_map:
            return
        
        output_lookup = {entry['measurement_type']: entry['output_key'] for entry in plan}
        
        # ⚠️ CONFLICT DETECTION: Lấy model_class từ instances để kiểm tra field
        model_class = instances[0].__class__ if instances else None
        import logging
        logger = logging.getLogger(__name__)
        
        for result_item in result_list:
            instance_id = result_item.get('id')
            if instance_id is None:
                continue
            instance_measurements = measurement_map.get(instance_id)
            if not instance_measurements:
                continue
            for measurement_type, formatted_value in instance_measurements.items():
                output_key = output_lookup.get(measurement_type, measurement_type)
                
                # ⚠️ CONFLICT DETECTION: Phân biệt rõ ràng giữa field của model và measurement_type
                if output_key in result_item and result_item[output_key] not in (None, ''):
                    # Kiểm tra xem đây có phải là field của model không
                    if model_class and cls._is_model_field(model_class, output_key):
                        # Đây là field của model, skip measurement và log warning
                        logger.debug(
                            f"[MeasurableDynamicSchema] Skipping measurement '{measurement_type}' "
                            f"because model field '{output_key}' already has value in {model_class.__name__}"
                        )
                        continue
                    # Nếu không phải field của model (có thể là annotation/computed field),
                    # vẫn có thể là measurement đã được set trước đó, nhưng cho phép override
                    # để đảm bảo measurement value được set đúng
                
                result_item[output_key] = formatted_value
    
    @classmethod
    def from_queryset(cls, queryset: Union[Model, QuerySet], many: bool = False, exclude: List[str] = None, 
                      measurement_types: List[str] = None, optimize_measurements: bool = True,
                      raw_measurements: bool = False, **kwargs) -> Union[Dict, List[Dict]]:
        """
        Extends the DynamicSchema.from_queryset method to include measurement data.
        Optimized for performance with bulk measurement loading.
        
        Args:
            queryset: The Django model instance or queryset
            many: Whether to process as a list of objects
            exclude: List of fields to exclude
            measurement_types: Specific measurement types to load (optional)
            optimize_measurements: Whether to use optimized bulk loading (default: True)
            raw_measurements: Only applies when many=False. If True, returns measurement data 
                            as object (already converted to user settings units). 
                            If False, returns formatted string. (default: False)
            
        Returns:
            If many=True, returns a list of dictionaries with model data
            If many=False, returns a dictionary with model data
        """
        # Check if we're dealing with a measurable model first
        model_class = queryset.model if isinstance(queryset, QuerySet) else (queryset[0].__class__ if isinstance(queryset, list) and queryset else queryset.__class__)
        is_measurable = hasattr(model_class, 'MEASUREMENT_TYPES') or hasattr(model_class, 'set_measurement')
        
        # ⚠️ CRITICAL: Handle duplicate rows if queryset is already a list (evaluated)
        # This happens when pagination evaluates queryset with prefetch_related('measurements')
        # 🚀 PERFORMANCE: Single-pass deduplication (O(n) instead of O(3n))
        if isinstance(queryset, list) and queryset and is_measurable:
            seen_ids: Dict[int, Model] = {}
            deduplicated: List[Model] = []
            has_duplicates = False
            
            for obj in queryset:
                obj_id = getattr(obj, 'id', None)
                if obj_id is None:
                    deduplicated.append(obj)
                    continue
                
                if obj_id not in seen_ids:
                    seen_ids[obj_id] = obj
                    deduplicated.append(obj)
                else:
                    has_duplicates = True
                    # Merge measurements from duplicate into first occurrence
                    existing_obj = seen_ids[obj_id]
                    if hasattr(obj, '_prefetched_objects_cache') and 'measurements' in obj._prefetched_objects_cache:
                        if not hasattr(existing_obj, '_prefetched_objects_cache'):
                            existing_obj._prefetched_objects_cache = {}
                        if 'measurements' not in existing_obj._prefetched_objects_cache:
                            existing_obj._prefetched_objects_cache['measurements'] = []
                        # Merge measurements
                        existing_obj._prefetched_objects_cache['measurements'].extend(
                            obj._prefetched_objects_cache['measurements']
                        )
            
            if has_duplicates:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"[MeasurableDynamicSchema] ⚠️ Detected duplicate rows in list (likely due to measurements prefetch). "
                              f"Deduplicating {len(queryset)} rows into {len(deduplicated)} unique records.")
                queryset = deduplicated
        
        # IMPORTANT: Always get base result first to preserve all fields including sortable ones
        # 🚀 ENHANCED: Optimize queryset to prefetch measurements AND M2M fields
        if isinstance(queryset, QuerySet):
            # ⚠️ CRITICAL: Do NOT prefetch measurements here - it causes duplicate rows
            # Measurements will be fetched separately after getting base data
            # if hasattr(queryset.model, 'measurements'):
            #     queryset = queryset.prefetch_related('measurements')
            
            # 🔄 RESTORED M2M LOGIC: Add M2M prefetch optimization (but NOT measurements)
            m2m_prefetch_fields = cls._get_m2m_prefetch_fields(queryset.model)
            if m2m_prefetch_fields:
                queryset = queryset.prefetch_related(*m2m_prefetch_fields)
        
        # Get the base result from parent class - this preserves ALL fields including sortable ones
        # Pass through all kwargs to ensure proper field handling
        # ⚠️ CRITICAL: Filter out kwargs that cause recursion (request_path, query_fields, model_class, etc.)
        # Also disable dynamic optimization to prevent recursion
        recursion_causing_kwargs = {'request_path', 'query_fields', 'default_fields', 'tab', 'model_class', 'auto_resolve_fields'}
        
        # Filter kwargs to avoid recursion
        filtered_kwargs = {k: v for k, v in kwargs.items() if k not in recursion_causing_kwargs}
        
        base_kwargs = {
            k: v for k, v in locals().items() 
            if k not in ['cls', 'queryset', 'many', 'exclude', 'measurement_types', 'optimize_measurements', 'raw_measurements', 'kwargs']
        }
        
        # Add filtered kwargs to base_kwargs
        base_kwargs.update(filtered_kwargs)
        
        # ⚠️ CRITICAL: Disable dynamic optimization to prevent recursion
        base_kwargs['auto_resolve_fields'] = False
        
        # Ensure we pass through all necessary parameters for proper field handling
        if 'exclude' not in base_kwargs:
            base_kwargs['exclude'] = exclude

        # 🚀 CRITICAL: Always call parent class first to preserve ALL formatting and processing
        # For many=False, DynamicSchema will handle queryset.first() internally, so we just pass queryset
        result = None
        
        # 🎯 SMART HANDLING: Detect measurements GenericRelation separately from regular M2M fields
        # measurements là GenericRelation (ContentType-based), không phải ManyToManyField
        # Cần xử lý riêng để tránh duplicate khi dùng .values()
        has_measurements_field = False
        if isinstance(queryset, QuerySet):
            model = queryset.model
            # Check if model has measurements GenericRelation field
            try:
                from django.contrib.contenttypes.fields import GenericRelation
                measurements_field = model._meta.get_field('measurements')
                if isinstance(measurements_field, GenericRelation):
                    has_measurements_field = True
            except (AttributeError, Exception):
                pass
            
            # Also check if measurements is prefetched
            if hasattr(queryset, '_prefetch_related_lookups') and 'measurements' in queryset._prefetch_related_lookups:
                has_measurements_field = True
        
        # 🎯 SMART STRATEGY: If we have measurements, we need special handling
        # ⚠️ CRITICAL: When queryset has prefetch_related('measurements'), evaluating it will create duplicate rows
        # Solution: Remove measurements from prefetch BEFORE processing, then fetch measurements separately
        if has_measurements_field and isinstance(queryset, QuerySet):
            # ⚠️ CRITICAL FIX: Remove measurements from prefetch to prevent duplicate rows
            # We'll fetch measurements separately after getting base data
            if hasattr(queryset, '_prefetch_related_lookups') and 'measurements' in queryset._prefetch_related_lookups:
                # 🆕 SIMPLE FIX: Just modify _prefetch_related_lookups in place (don't rebuild queryset)
                # This preserves ALL query state including annotations, select_related, etc.
                queryset._prefetch_related_lookups = tuple(
                    p for p in queryset._prefetch_related_lookups if p != 'measurements'
                )
            
            # Mark that we have measurements so DynamicSchema can handle it appropriately
            base_kwargs['_has_measurements_field'] = True
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"[MeasurableDynamicSchema] ℹ️ Removed measurements prefetch for {model_class.__name__}. "
                       f"Measurements will be fetched separately.")
        
        try:
            # 🔄 ENHANCED: Ensure we pass through all necessary kwargs for proper inheritance
            # ⚠️ CRITICAL: Do NOT evaluate queryset before calling super() - let DynamicSchema handle it
            # Evaluating queryset.count() here could conflict with DynamicSchema's internal logic
            result = super().from_queryset(queryset, many=many, **base_kwargs)
            
            # 🚀 PERFORMANCE: Calculate record count AFTER result is available (safe and accurate)
            # This ensures we don't interfere with DynamicSchema's queryset evaluation logic
            record_count = 0
            if many and isinstance(result, list):
                record_count = len(result)
            elif not many and result:
                record_count = 1
            elif many and isinstance(queryset, QuerySet):
                # Fallback: only if result is not a list (shouldn't happen, but safe)
                # Check if queryset was already evaluated by DynamicSchema
                if queryset._result_cache is not None:
                    record_count = len(queryset._result_cache)
                else:
                    # Last resort: count (but this should rarely happen)
                    try:
                        record_count = queryset.count()
                    except:
                        record_count = 0
                
            
        except Exception as e:
            # Only fallback if parent class completely fails
            import traceback
            traceback.print_exc()
            
            # 🔄 ENHANCED: Try enhanced fallback methods with full DynamicSchema inheritance
            try:
                if many and isinstance(queryset, QuerySet):
                    result = cls._create_schema_from_queryset_fallback(queryset, exclude)
                elif not many:
                    if isinstance(queryset, QuerySet):
                        instance = queryset.first()
                        if instance:
                            result = cls._create_schema_from_instance_fallback(instance, exclude)
                    elif hasattr(queryset, '__class__'):
                        result = cls._create_schema_from_instance_fallback(queryset, exclude)
                    
            except Exception as fallback_error:
                import traceback
                traceback.print_exc()
                result = None
        
        if not result:
            return result
        
        # If not measurable, just return base result
        if not is_measurable:
            return result
        
        # Get measurement types from the model class if not provided
        if not measurement_types:
            measurement_types = getattr(model_class, 'MEASUREMENT_TYPES', [])

        # Process measurements
        if measurement_types:
            if optimize_measurements and isinstance(queryset, QuerySet) and many and measurement_types:
                cls._bulk_load_measurements_optimized(queryset, result, measurement_types, raw_measurements=False)
            else:
                if many:
                    cls._bulk_process_measurements(queryset, result, measurement_types, raw_measurements=False)
                else:
                    # Get instance for measurement processing
                    instance = queryset.first() if isinstance(queryset, QuerySet) else queryset
                    if instance:
                        cls._add_measurement_data(instance, result, many=False, measurement_types=measurement_types, raw_measurements=raw_measurements)

        return result
    
    @classmethod
    def _create_schema_from_queryset_fallback(cls, queryset: QuerySet, exclude: List[str] = None) -> List[Dict]:
        """
        🔄 RESTORED: Enhanced fallback with full DynamicSchema inheritance
        
        This fallback method now properly inherits ALL DynamicSchema capabilities:
        - User settings loading and caching
        - Exchange rates caching  
        - M2M field processing with prefetch detection
        - All formatting methods including currency, datetime, numbers
        - Field exclusion logic matching DynamicSchema
        
        INHERITANCE FLOW:
        1. Try to delegate to parent's processing methods if available
        2. Use enhanced fallback with proper DynamicSchema formatting
        3. Maintain all MeasurableDynamicSchema-specific features
        """
        
        result = []
        exclude = exclude or []
        
        try:
            # 🚀 CRITICAL: Try to use parent class processing logic first
            if hasattr(cls.__bases__[0], '_process_single_item_for_queryset'):
                # print(f"🚀 [Fallback] Using parent class _process_single_item_for_queryset")
                # Get parent class processing dependencies
                is_core_user = False
                supports_multilanguage = False
                current_language = 'en'
                select_related_fields = []
                
                def should_exclude(field_name):
                    return field_name in exclude
                
                # Use inherited settings loading
                user_settings = None  # DEPRECATED: No longer used
                exchange_rates = super()._get_cached_exchange_rates(None) if hasattr(super(), '_get_cached_exchange_rates') else None
                
                for obj in queryset:
                    item_result = cls.__bases__[0]._process_single_item_for_queryset(
                        obj, is_core_user, should_exclude, select_related_fields,
                        supports_multilanguage, current_language, exchange_rates, user_settings, many=True
                    )
                    result.append(item_result)
                
                return result
            
        except Exception as e:
            # print(f"⚠️ [Fallback] Parent class processing failed: {e}, using enhanced local fallback")
            pass
        
        # 🔄 ENHANCED FALLBACK: Use proper DynamicSchema inheritance
        user_settings = None
        exchange_rates = None
        try:
            # Use proper inheritance for settings loading
            user_settings = super()._get_user_settings()
            exchange_rates = super()._get_cached_exchange_rates(None)
        except Exception:
            # Fallback to direct import if inheritance fails
            try:
                from core.common.schema_utils import DynamicSchema
                user_settings = DynamicSchema._get_user_settings()
                exchange_rates = DynamicSchema._get_cached_exchange_rates(None)
            except Exception:
                pass
        
        for obj in queryset:
            item = {}
            
            # Kiểm tra xem obj có phải là dict không
            if isinstance(obj, dict):
                # Nếu là dict, copy trực tiếp và format values
                for key, value in obj.items():
                    if key not in exclude:
                        item[key] = cls._format_value_with_parent(value, key, None, exchange_rates, user_settings)
                result.append(item)
                continue
            
            # Lấy tất cả fields từ model (chỉ khi obj là Django model instance)
            if not isinstance(obj, models.Model):
                # Nếu không phải model, skip
                continue
                
            for field in obj._meta.fields:
                if field.name not in exclude:
                    try:
                        value = getattr(obj, field.name)
                        # ⚡ ENHANCED: Use DynamicSchema formatting instead of basic serialization
                        item[field.name] = cls._format_value_with_parent(value, field.name, field, exchange_rates, user_settings)
                    except Exception as e:
                        # print(f"⚠️ [Fallback] Error getting field {field.name}: {e}")
                        item[field.name] = None
            
            # Lấy annotations (computed fields)
            for key, value in obj.__dict__.items():
                if key.startswith('_') or key in exclude:
                    continue
                if key not in item:
                    # ⚡ ENHANCED: Use DynamicSchema formatting for annotations
                    item[key] = cls._format_value_with_parent(value, key, None, exchange_rates, user_settings)
            
            # 🔄 RESTORED M2M LOGIC: Handle ManyToManyField fields using DynamicSchema logic
            from django.db.models import ManyToManyField
            
            for field in obj._meta.get_fields():
                if hasattr(field, 'name') and field.name not in exclude:
                    try:
                        # 🚀 ENHANCED: Use proper ManyToManyField detection like DynamicSchema
                        if isinstance(field, ManyToManyField):
                            field_name = field.name
                            try:
                                # Always add _ids version - EXACT MATCH với DynamicSchema logic
                                m2m_ids = list(getattr(obj, field_name).values_list('id', flat=True))
                                item[f"{field_name}_ids"] = m2m_ids
                                
                                # 🔄 RESTORED: Use DynamicSchema's _create_dynamic_m2m_schema method
                                try:
                                    # Use lightweight M2M processing in fallback
                                    m2m_objects = getattr(obj, field_name, None)
                                    if m2m_objects and hasattr(m2m_objects, 'all'):
                                        m2m_list = list(m2m_objects.all()[:10])  # Limit to prevent performance issues
                                        
                                        if m2m_list:
                                            # 🚀 CRITICAL: Use parent class _create_dynamic_m2m_schema
                                            from core.common.schema_utils import DynamicSchema
                                            related_model = field.related_model
                                            dynamic_schema_class = DynamicSchema._create_dynamic_m2m_schema(related_model)
                                            
                                            # Serialize using dynamic schema - EXACT MATCH với DynamicSchema
                                            m2m_data = []
                                            for m2m_obj in m2m_list:
                                                obj_data = dynamic_schema_class.from_queryset(m2m_obj, many=False, exchange_rates=exchange_rates, user_settings=None)  # DEPRECATED: No longer used
                                                if obj_data:
                                                    m2m_data.append(obj_data)
                                            
                                            item[field_name] = m2m_data
                                        else:
                                            item[field_name] = []
                                    else:
                                        item[field_name] = []
                                except Exception as e:
                                    # print(f"⚠️ [Fallback M2M] Error processing M2M objects for {field_name}: {e}")
                                    item[field_name] = []
                            except Exception as e:
                                # print(f"⚠️ [Fallback M2M] Error processing M2M field {field_name}: {e}")
                                item[f"{field_name}_ids"] = []
                                item[field_name] = []
                    except Exception as e:
                        # print(f"⚠️ [Fallback] Error processing M2M field {field.name}: {e}")
                        pass
            
            # Lấy related fields (ForeignKey, OneToOne)
            for field in obj._meta.related_objects:
                if field.name not in exclude:
                    try:
                        related_obj = getattr(obj, field.name)
                        if related_obj:
                            if hasattr(related_obj, 'id'):
                                item[f"{field.name}_id"] = related_obj.id
                                if hasattr(related_obj, 'name'):
                                    # ⚡ ENHANCED: Format related field names
                                    item[f"{field.name}_name"] = cls._format_value_with_parent(related_obj.name, f"{field.name}_name", None, exchange_rates, user_settings)
                        else:
                            item[f"{field.name}_id"] = None
                    except Exception as e:
                        # print(f"⚠️ [Fallback] Error getting related field {field.name}: {e}")
                        pass
            
            result.append(item)
        return result
    
    @classmethod
    def _create_schema_from_instance_fallback(cls, instance, exclude: List[str] = None) -> Dict:
        """
        🔄 RESTORED: Enhanced single instance fallback with full DynamicSchema inheritance
        
        This method now properly inherits from DynamicSchema's single item processing
        while maintaining MeasurableDynamicSchema-specific enhancements.
        
        INHERITANCE FEATURES:
        - Uses DynamicSchema._process_single_item_for_queryset if available
        - Falls back to enhanced local processing with DynamicSchema formatting
        - Maintains all M2M field processing
        - Preserves measurement field processing
        """
        item = {}
        exclude = exclude or []
        
        try:
            # 🚀 CRITICAL: Try to use parent class processing logic first
            if hasattr(cls.__bases__[0], '_process_single_item_for_queryset'):
                # print(f"🚀 [Instance Fallback] Using parent class _process_single_item_for_queryset")
                
                # Setup parent class processing dependencies
                is_core_user = False
                supports_multilanguage = False
                current_language = 'en'
                select_related_fields = []
                
                def should_exclude(field_name):
                    return field_name in exclude
                
                # Use inherited settings loading
                user_settings = None  # DEPRECATED: No longer used
                exchange_rates = super()._get_cached_exchange_rates(None) if hasattr(super(), '_get_cached_exchange_rates') else None
                
                return cls.__bases__[0]._process_single_item_for_queryset(
                    instance, is_core_user, should_exclude, select_related_fields,
                    supports_multilanguage, current_language, exchange_rates, user_settings, many=False
                )
            
        except Exception as e:
            # print(f"⚠️ [Instance Fallback] Parent class processing failed: {e}, using enhanced local fallback")
            pass
        
        # 🔄 ENHANCED FALLBACK: Use proper DynamicSchema inheritance
        user_settings = None
        exchange_rates = None
        try:
            # Use proper inheritance for settings loading
            user_settings = super()._get_user_settings()
            exchange_rates = super()._get_cached_exchange_rates(None)
        except Exception:
            # Fallback to direct import if inheritance fails
            try:
                from core.common.schema_utils import DynamicSchema
                user_settings = DynamicSchema._get_user_settings()
                exchange_rates = DynamicSchema._get_cached_exchange_rates(None)
            except Exception:
                pass
        
        # Lấy tất cả fields từ model
        for field in instance._meta.fields:
            if field.name not in exclude:
                try:
                    value = getattr(instance, field.name)
                    # ⚡ ENHANCED: Use DynamicSchema formatting instead of basic serialization
                    item[field.name] = cls._format_value_with_parent(value, field.name, field, exchange_rates, user_settings)
                except Exception as e:
                    # print(f"⚠️ [Fallback] Error getting field {field.name}: {e}")
                    item[field.name] = None
        
        # Lấy annotations (computed fields)
        for key, value in instance.__dict__.items():
            if key.startswith('_') or key in exclude:
                continue
            if key not in item:
                # ⚡ ENHANCED: Use DynamicSchema formatting for annotations
                item[key] = cls._format_value_with_parent(value, key, None, exchange_rates, user_settings)
        
        # 🔄 RESTORED M2M LOGIC: Handle ManyToManyField fields for single instance using DynamicSchema logic
        from django.db.models import ManyToManyField
        
        for field in instance._meta.get_fields():
            if hasattr(field, 'name') and field.name not in exclude:
                try:
                    # 🚀 ENHANCED: Use proper ManyToManyField detection like DynamicSchema
                    if isinstance(field, ManyToManyField):
                        field_name = field.name
                        try:
                            # Always add _ids version - EXACT MATCH với DynamicSchema logic
                            m2m_ids = list(getattr(instance, field_name).values_list('id', flat=True))
                            item[f"{field_name}_ids"] = m2m_ids
                            
                            # 🔄 RESTORED: Use DynamicSchema's _create_dynamic_m2m_schema method for single instance
                            try:
                                # Use lightweight M2M processing in fallback
                                m2m_objects = getattr(instance, field_name, None)
                                if m2m_objects and hasattr(m2m_objects, 'all'):
                                    m2m_list = list(m2m_objects.all()[:10])  # Limit to prevent performance issues
                                    
                                    if m2m_list:
                                        # 🚀 CRITICAL: Use parent class _create_dynamic_m2m_schema
                                        from core.common.schema_utils import DynamicSchema
                                        related_model = field.related_model
                                        dynamic_schema_class = DynamicSchema._create_dynamic_m2m_schema(related_model)
                                        
                                        # Serialize using dynamic schema - EXACT MATCH với DynamicSchema
                                        m2m_data = []
                                        for m2m_obj in m2m_list:
                                            obj_data = dynamic_schema_class.from_queryset(m2m_obj, many=False, exchange_rates=exchange_rates, user_settings=None)  # DEPRECATED: No longer used
                                            if obj_data:
                                                m2m_data.append(obj_data)
                                        
                                        item[field_name] = m2m_data
                                    else:
                                        item[field_name] = []
                                else:
                                    item[field_name] = []
                            except Exception as e:
                                # print(f"⚠️ [Fallback M2M] Error processing M2M objects for {field_name}: {e}")
                                item[field_name] = []
                        except Exception as e:
                            # print(f"⚠️ [Fallback M2M] Error processing M2M field {field_name}: {e}")
                            item[f"{field_name}_ids"] = []
                            item[field_name] = []
                except Exception as e:
                    # print(f"⚠️ [Fallback] Error processing M2M field {field.name}: {e}")
                    pass
        
        return item
    
    @classmethod
    def _format_value_with_parent(cls, value, field_name=None, field_obj=None, exchange_rates=None, user_settings=None):
        """
        🔄 RESTORED: Format value using DynamicSchema's centralized formatting
        
        This method properly inherits DynamicSchema's formatting capabilities ensuring
        consistent formatting across both normal and measurable fields.
        
        INHERITANCE CHAIN:
        1. Try DynamicSchema._centralized_format_value (main formatting method)
        2. Try DynamicSchema._make_json_serializable (alternative formatting method) 
        3. Fallback to basic serialization only if parent methods fail
        
        This ensures MeasurableDynamicSchema gets all formatting features from DynamicSchema.
        """
        try:
            # 🚀 CRITICAL: Direct parent class method call for proper inheritance
            return super()._centralized_format_value(value, field_name, field_obj, exchange_rates, user_settings)
        except (AttributeError, Exception) as e:
            # If _centralized_format_value is not available, try _make_json_serializable
            try:
                return super()._make_json_serializable(value, field_name, field_obj, exchange_rates, user_settings)
            except (AttributeError, Exception) as e2:
                # Final fallback: use basic serialization
                # print(f"⚠️ [Formatting] Parent formatting methods unavailable: {e}, {e2}. Using basic serialization")
                return cls._serialize_value(value)
    
    @classmethod 
    def _get_m2m_prefetch_fields(cls, model):
        """
        🔄 RESTORED M2M LOGIC: Enhanced prefetch logic using DynamicSchema intelligence
        
        This method now properly inherits from DynamicSchema._get_required_prefetch_related
        while adding measurable-model-specific enhancements.
        
        INHERITANCE FEATURES:
        - Uses DynamicSchema._get_required_prefetch_related as base logic
        - Adds measurable-specific M2M field detection
        - Maintains caching for performance
        
        Args:
            model: Django model class to analyze
            
        Returns:
            List[str]: List of field names to prefetch_related
        """
        cache_key = f"_m2m_prefetch_cache_{model.__name__}"
        if hasattr(cls, cache_key):
            return getattr(cls, cache_key)
        
        prefetch_fields = []
        
        try:
            # 🚀 CRITICAL: Try to use parent class prefetch logic first
            if hasattr(cls.__bases__[0], '_get_required_prefetch_related'):
                prefetch_fields = cls.__bases__[0]._get_required_prefetch_related(model)
                # print(f"🚀 [M2M Prefetch] Using DynamicSchema logic, found {len(prefetch_fields)} fields: {prefetch_fields}")
            else:
                # print(f"⚠️ [M2M Prefetch] Parent method not available, using enhanced fallback")
                pass
        except Exception as e:
            # print(f"⚠️ [M2M Prefetch] Parent method failed: {e}, using enhanced fallback")
            pass
        
        # 🔄 ENHANCED: Add measurable-specific M2M fields
        measurable_specific_fields = set()
        
        # Add project-specific measurable fields
        measurable_m2m_fields = {
            'cargo_compartments', 'specifications', 'measurements', 
            'attachments', 'features', 'options', 'variants'
        }
        
        try:
            from django.db.models import ManyToManyField
            
            for field in model._meta.get_fields():
                if hasattr(field, 'many_to_many') and field.many_to_many:
                    field_name = field.name
                    
                    # Add measurable-specific M2M fields not caught by parent
                    if (field_name in measurable_m2m_fields and 
                        field_name not in prefetch_fields):
                        measurable_specific_fields.add(field_name)
                    
                    # Add M2M fields for measurable models (they often have related data)
                    elif (hasattr(model, 'MEASUREMENT_TYPES') and 
                          field_name not in prefetch_fields and 
                          len(field_name) <= 15):  # Reasonable length check
                        measurable_specific_fields.add(field_name)
                        
        except Exception as e:
            # print(f"⚠️ [M2M Prefetch] Error analyzing measurable fields for {model.__name__}: {e}")
            pass
        
        # Combine parent prefetch fields with measurable-specific ones
        final_prefetch_fields = list(set(prefetch_fields) | measurable_specific_fields)
        
        if measurable_specific_fields:
            # print(f"📊 [M2M Prefetch] Added measurable-specific fields: {list(measurable_specific_fields)}")
            pass
        # Cache the result to avoid repeated processing
        setattr(cls, cache_key, final_prefetch_fields)
        
        return final_prefetch_fields
    
    @classmethod
    def _serialize_m2m_object_simple(cls, m2m_obj, exchange_rates=None, user_settings=None):
        """
        🔄 RESTORED M2M LOGIC: Enhanced M2M object serialization using DynamicSchema methods
        
        This method now properly inherits from DynamicSchema's M2M processing logic
        while maintaining compatibility with MeasurableDynamicSchema requirements.
        
        INHERITANCE FEATURES:
        - Uses DynamicSchema._serialize_m2m_object_lightweight if available
        - Falls back to enhanced local processing with DynamicSchema formatting
        - Maintains all original field processing logic
        
        Args:
            m2m_obj: The ManyToMany related object to serialize
            exchange_rates: Exchange rates for currency conversion (optional)
            user_settings: User settings for formatting (optional)
            
        Returns:
            Dict: Properly formatted M2M object data
        """
        if not m2m_obj:
            return None
        
        try:
            # 🚀 CRITICAL: Try to use parent class M2M serialization method first
            if hasattr(cls.__bases__[0], '_serialize_m2m_object_lightweight'):
                return cls.__bases__[0]._serialize_m2m_object_lightweight(m2m_obj, exchange_rates, user_settings)
        except Exception as e:
            # print(f"⚠️ [M2M Serialization] Parent method failed: {e}, using enhanced fallback")
            pass
        
        # 🔄 ENHANCED FALLBACK: Use DynamicSchema formatting for all fields
        result = {'id': getattr(m2m_obj, 'id', None)}
        
        # Add commonly needed fields with full DynamicSchema formatting
        basic_fields = ['name', 'title', 'code', 'slug', 'description', 'status', 'type']
        for field_name in basic_fields:
            if hasattr(m2m_obj, field_name):
                value = getattr(m2m_obj, field_name, None)
                if value is not None:
                    # 🚀 CRITICAL: Use proper parent formatting for consistency
                    result[field_name] = cls._format_value_with_parent(value, field_name, None, exchange_rates, user_settings)
        
        # 🔄 RESTORED: Add translation support like DynamicSchema
        try:
            from core.middleware.refresh_token import get_current_request
            
            if (hasattr(m2m_obj, 'TRANSLATABLE_FIELDS') and 
                hasattr(m2m_obj, 'get_translation')):
                request = get_current_request()
                current_language = getattr(request, 'LANGUAGE_CODE', 'en') if request else 'en'
                
                for field_name in basic_fields:
                    if (field_name in m2m_obj.TRANSLATABLE_FIELDS and 
                        field_name not in result):
                        try:
                            # Use parent class translation method if available
                            if hasattr(cls.__bases__[0], '_get_related_field_translation'):
                                translation = cls.__bases__[0]._get_related_field_translation(m2m_obj, field_name, current_language)
                            else:
                                # Fallback translation logic
                                translation = getattr(m2m_obj, field_name, None)
                            
                            if translation:
                                result[field_name] = cls._format_value_with_parent(translation, field_name, None, exchange_rates, user_settings)
                        except Exception:
                            pass
        except Exception:
            pass
        
        # Add model type info for debugging
        result['__model_type'] = m2m_obj.__class__.__name__
        
        return result
    
    @classmethod
    def _serialize_value(cls, value):
        """
        Serialize value thành primitive type có thể JSON serialize được.
        """
        if value is None:
            return None
        
        # Django model instances
        if hasattr(value, '_meta') and hasattr(value, 'id'):
            return {
                'id': value.id,
                'name': getattr(value, 'name', str(value)),
                'type': value.__class__.__name__
            }
        
        # Django QuerySet
        if hasattr(value, 'values_list'):
            return list(value.values_list('id', flat=True))
        
        # Datetime objects
        if hasattr(value, 'isoformat'):
            return value.isoformat()
        
        # Decimal objects
        if hasattr(value, 'quantize'):
            return float(value)
        
        # UUID objects
        if hasattr(value, 'hex'):
            return str(value)
        
        # List, tuple
        if isinstance(value, (list, tuple)):
            return [cls._serialize_value(item) for item in value]
        
        # Dict
        if isinstance(value, dict):
            return {k: cls._serialize_value(v) for k, v in value.items()}
        
        # Primitive types
        if isinstance(value, (str, int, float, bool)):
            return value
        
        # Fallback: convert to string
        return str(value)
    

    
    @classmethod
    def _bulk_load_measurements_optimized(cls, queryset: QuerySet, result_list: List[Dict], 
                                         measurement_types: List[str], raw_measurements: bool = False) -> None:
        """
        Bulk load measurements for all objects in the queryset using optimized database queries.
        This method reduces N+1 query problem to just 1 query per measurement type.
        IMPORTANT: This method only adds/updates measurement fields, preserving all other fields.
        
        Args:
            queryset: The QuerySet containing the objects
            result_list: List of result dictionaries to update (already containing base fields)
            measurement_types: List of measurement types to load
            raw_measurements: If True and many=False, returns object. Always False for many=True.
        """
        if not result_list or not measurement_types:
            return
        
        instances = []
        if isinstance(queryset, QuerySet):
            if queryset._result_cache is not None:
                instances = list(queryset._result_cache)
            else:
                instances = list(queryset)
        elif isinstance(queryset, list):
            instances = queryset
        else:
            instances = [queryset]

        if not instances or not result_list:
            return

        model_class = instances[0].__class__
        normalized_types = cls._normalize_measurement_types(measurement_types, model_class)
        plan = cls._get_measurement_plan(model_class, normalized_types, raw_measurements=False, many=True)
        if not plan:
            return

        cls._apply_measurement_plan_to_many(instances, result_list, plan)
    
    @classmethod
    def _bulk_process_measurements(cls, queryset: Union[QuerySet, List[Model]], result_list: List[Dict], measurement_types: List[str] = None, raw_measurements: bool = False) -> None:
        """
        Process measurements for multiple instances in bulk for better performance.
        This method is used as fallback when optimized loading is not available.
        
        Args:
            queryset: QuerySet or list of model instances
            result_list: List of dictionaries to update with measurement data
            measurement_types: List of measurement types to process (optional)
            raw_measurements: If True and many=False, returns object. Always False for many=True.
        """
        if isinstance(queryset, QuerySet):
            if queryset._result_cache is not None:
                instances = list(queryset._result_cache)
            else:
                instances = list(queryset)
        elif isinstance(queryset, list):
            instances = queryset
        else:
            instances = [queryset]

        if not instances or not result_list:
            return

        model_class = instances[0].__class__
        normalized_types = cls._normalize_measurement_types(measurement_types, model_class)
        plan = cls._get_measurement_plan(model_class, normalized_types, raw_measurements=False, many=True)
        if not plan:
            return

        cls._apply_measurement_plan_to_many(instances, result_list, plan)
    
    @classmethod
    def _add_measurement_data(cls, instance: Model, result_dict: Dict, many: bool, measurement_types: List[str] = None, raw_measurements: bool = False) -> None:
        """
        Adds measurement data to the result dictionary with optimized access to prefetched data.
        
        Args:
            instance: The model instance
            result_dict: The dictionary to add measurement data to
            many: Whether processing multiple objects
            measurement_types: List of measurement types to process (optional)
            raw_measurements: Only applies when many=False. If True, returns measurement object 
                            (already converted to user settings units). If False, returns formatted string.
        """
        normalized_types = cls._normalize_measurement_types(measurement_types, instance.__class__)
        plan = cls._get_measurement_plan(instance.__class__, normalized_types, raw_measurements, many)
        if not plan:
            return

        value_map = cls._collect_measurements_in_batch([instance], plan)
        instance_id = getattr(instance, 'id', None)
        if instance_id is None:
            return
        measurements_for_instance = value_map.get(instance_id, {})
        
        # ⚠️ CONFLICT DETECTION: Lấy model_class để kiểm tra field
        model_class = instance.__class__
        import logging
        logger = logging.getLogger(__name__)
        
        for entry in plan:
            output_key = entry['output_key']
            
            # ⚠️ CONFLICT DETECTION: Phân biệt rõ ràng giữa field của model và measurement_type
            if output_key in result_dict and result_dict[output_key] not in (None, ''):
                # Kiểm tra xem đây có phải là field của model không
                if cls._is_model_field(model_class, output_key):
                    # Đây là field của model, skip measurement và log warning
                    logger.debug(
                        f"[MeasurableDynamicSchema] Skipping measurement '{entry['measurement_type']}' "
                        f"because model field '{output_key}' already has value in {model_class.__name__}"
                    )
                    continue
                # Nếu không phải field của model (có thể là annotation/computed field),
                # vẫn có thể là measurement đã được set trước đó, nhưng cho phép override
                # để đảm bảo measurement value được set đúng
            
            measurement_value = measurements_for_instance.get(entry['measurement_type'])
            if measurement_value is not None:
                result_dict[output_key] = measurement_value
    
    @classmethod
    def optimize_queryset_for_measurements(cls, queryset: QuerySet) -> QuerySet:
        """
        Optimize a queryset for fetching measurement data by adding appropriate prefetch_related.
        
        Args:
            queryset: The queryset to optimize
            
        Returns:
            QuerySet: Optimized queryset with prefetch_related for measurements
        """
        if hasattr(queryset.model, 'measurements'):
            return queryset.prefetch_related(
                Prefetch('measurements')
            )
        return queryset
    
    @classmethod
    def to_drf_serializer_data(cls, queryset: Union[Model, QuerySet], many: bool = False, exclude: List[str] = None) -> Union[Dict, List[Dict]]:
        """
        Convenience method to integrate with Django REST Framework serializers.
        Converts a queryset or model instance to serializer data with measurement fields.
        
        Args:
            queryset: The Django model instance or queryset
            many: Whether to process as a list of objects
            exclude: List of fields to exclude
            
        Returns:
            Dictionary or list of dictionaries with model data including measurements
        """
        # First optimize the queryset
        if isinstance(queryset, QuerySet):
            queryset = cls.optimize_queryset_for_measurements(queryset)
            
        # Then process with measurements
        return cls.from_queryset(queryset, many=many, exclude=exclude)