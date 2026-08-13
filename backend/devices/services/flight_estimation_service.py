
"""Utilities for estimating flight capabilities of devices.

This module focuses on read-only computations that combine measurements from
different components (propulsion, flight performance, weather inputs).

The service is written to be efficient for bulk usage (hundreds/thousands of
devices). To avoid N+1 issues, always prefetch related measurements before
invoking the estimation helpers, for example:

    Device.objects.select_related('propulsion_system', 'flight_performance')\
        .prefetch_related(
            'propulsion_system__measurements',
            'flight_performance__measurements',
        )

"""

from __future__ import annotations

import copy
from decimal import Decimal
from functools import lru_cache
from typing import Any, Dict, Optional, Tuple

from django.core.exceptions import ObjectDoesNotExist

from common.utils import get_waypoint_speed
from devices.models import Device, Measurement
from devices.utils import convert_unit


class FlightEstimationService:
    """High-level helpers for flight time and range estimation."""

    @staticmethod
    def estimate_duration_for_distance(
        device: Device,
        distance_m: float,
        wind_speed_kmh: Optional[float] = None,
        default_cruise_speed: Optional[float] = None,
        user_units: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Estimate flight duration and feasibility for a specific distance.

        Args:
            device: The device instance (prefetch related measurements for best performance).
            distance_m: Target distance in meters.
            wind_speed_kmh: Optional wind speed (km/h) to validate against wind resistance.
            default_cruise_speed: Optional fallback cruise speed in m/s. If omitted, the
                value is retrieved from AdminConfig via :func:`common.utils.get_waypoint_speed`.
            user_units: Optional unit preference mapping (hierarchical structure). When not
                provided, the system-wide unit preferences are applied if available.

        Returns:
            Dict of computed metrics including estimated duration, constraint checks, and
            diagnostic information. Missing measurements are represented by ``None`` and
            do not automatically fail the feasibility check.
        """

        distance_m_value = FlightEstimationService._to_positive_float(distance_m)
        if distance_m_value is None:
            distance_m_value = 0.0

        resolved_user_units = FlightEstimationService._resolve_user_units(user_units)

        # Build measurement caches once per component.
        propulsion_measurements = FlightEstimationService._get_measurement_map(
            device, 'propulsion_system'
        )
        performance_measurements = FlightEstimationService._get_measurement_map(
            device, 'flight_performance'
        )

        flight_time_s = FlightEstimationService._get_simple_value(
            propulsion_measurements.get('flight_time'),
            target_unit='s',
            user_units=resolved_user_units,
        )

        maximum_range_m = FlightEstimationService._get_simple_value(
            performance_measurements.get('maximum_range'),
            target_unit='m',
            user_units=resolved_user_units,
        )

        cruise_speed_ms = FlightEstimationService._get_simple_value(
            performance_measurements.get('cruise_speed'),
            target_unit='m/s',
            user_units=resolved_user_units,
        )
        cruise_speed_source = 'measurement'

        if not cruise_speed_ms or cruise_speed_ms <= 0:
            if default_cruise_speed is None:
                default_cruise_speed = get_waypoint_speed()
            cruise_speed_ms = FlightEstimationService._to_positive_float(default_cruise_speed)
            cruise_speed_source = 'admin_config' if cruise_speed_ms else 'unavailable'

        wind_resistance_ms = FlightEstimationService._get_simple_value(
            performance_measurements.get('wind_resistance'),
            target_unit='m/s',
            user_units=resolved_user_units,
        )

        wind_speed_ms = FlightEstimationService._normalize_wind_speed(wind_speed_kmh)

        estimated_duration_s = None
        if cruise_speed_ms and cruise_speed_ms > 0:
            if distance_m_value > 0:
                estimated_duration_s = distance_m_value / cruise_speed_ms
            else:
                estimated_duration_s = 0.0

        battery_ok = False
        if flight_time_s is not None and estimated_duration_s is not None:
            battery_ok = estimated_duration_s <= flight_time_s

        range_ok = True
        if maximum_range_m is not None:
            range_ok = distance_m_value <= maximum_range_m

        wind_ok = True
        if wind_resistance_ms is not None and wind_speed_ms is not None:
            wind_ok = wind_speed_ms <= wind_resistance_ms
        can_complete = bool(
            cruise_speed_ms
            and estimated_duration_s is not None
            and battery_ok
            and range_ok
            and wind_ok
        )

        warnings = []
        if cruise_speed_ms is None:
            warnings.append('Missing cruise speed; unable to compute duration.')
        if battery_ok is False:
            warnings.append('Estimated duration exceeds available flight time.')
        elif battery_ok is False:
            warnings.append('Flight time measurement unavailable; battery check skipped.')
        if range_ok is False:
            warnings.append('Distance exceeds maximum range measurement.')
        elif range_ok is False:
            warnings.append('Maximum range measurement unavailable; range check skipped.')
        if wind_ok is False:
            warnings.append('Wind speed exceeds device wind resistance threshold.')
        elif wind_ok is False and wind_speed_ms is not None:
            warnings.append('Wind resistance measurement unavailable; wind check skipped.')

        return {
            'distance_m': distance_m_value,
            'cruise_speed_ms': cruise_speed_ms,
            'cruise_speed_source': cruise_speed_source,
            'estimated_duration_s': estimated_duration_s,
            'estimated_duration_min': (
                estimated_duration_s / 60 if estimated_duration_s is not None else None
            ),
            'flight_time_s': flight_time_s,
            'maximum_range_m': maximum_range_m,
            'wind_speed_ms': wind_speed_ms,
            'wind_resistance_ms': wind_resistance_ms,
            'battery_ok': battery_ok,
            'range_ok': range_ok,
            'wind_ok': wind_ok,
            'time_margin_s': (
                flight_time_s - estimated_duration_s
                if flight_time_s is not None and estimated_duration_s is not None
                else None
            ),
            'range_margin_m': (
                maximum_range_m - distance_m_value
                if maximum_range_m is not None
                else None
            ),
            'wind_margin_ms': (
                wind_resistance_ms - wind_speed_ms
                if wind_resistance_ms is not None and wind_speed_ms is not None
                else None
            ),
            'can_complete': can_complete,
            'warnings': warnings,
            # 'unit_preferences': copy.deepcopy(resolved_user_units) if resolved_user_units else None,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _get_measurement_map(device: Device, attr_name: str) -> Dict[str, Measurement]:
        try:
            component = getattr(device, attr_name)
        except (AttributeError, ObjectDoesNotExist):
            component = None

        if not component:
            return {}

        cache_key = '_cached_measurement_map'
        cached_map: Optional[Dict[str, Measurement]] = getattr(component, cache_key, None)
        if cached_map is not None:
            return cached_map

        measurements_qs = getattr(component, 'measurements', None)
        if measurements_qs is None:
            measurement_map: Dict[str, Measurement] = {}
        else:
            measurement_list = list(measurements_qs.all())
            measurement_map = {m.measurement_type: m for m in measurement_list}

        setattr(component, cache_key, measurement_map)
        return measurement_map

    @staticmethod
    def _get_simple_value(
        measurement: Optional[Measurement],
        target_unit: Optional[str] = None,
        user_units: Optional[Dict[str, Any]] = None,
    ) -> Optional[float]:
        value, source_unit = FlightEstimationService._extract_measurement_value(
            measurement,
            user_units=user_units,
        )
        if value is None:
            return None
        return FlightEstimationService._convert_value(value, source_unit, target_unit)

    @staticmethod
    def _normalize_wind_speed(wind_speed_kmh: Optional[float]) -> Optional[float]:
        value = FlightEstimationService._to_float(wind_speed_kmh)
        if value is None:
            return None
        return value / 3.6

    @staticmethod
    def _to_positive_float(value: Any) -> Optional[float]:
        number = FlightEstimationService._to_float(value)
        if number is None:
            return None
        if number <= 0:
            return None
        return number

    @staticmethod
    def _to_float(value: Any) -> Optional[float]:
        if value is None:
            return None
        if isinstance(value, bool):
            return float(value)
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, Decimal):
            return float(value)
        try:
            return float(str(value))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _extract_measurement_value(
        measurement: Optional[Measurement],
        user_units: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Optional[float], Optional[str]]:
        if not measurement or not isinstance(measurement, Measurement):
            return None, None

        numeric_value: Optional[float] = None
        unit: Optional[str] = None

        try:
            numeric_value = measurement.get_numeric_value(user_units=user_units)
        except Exception:
            numeric_value = None

        try:
            converted = measurement.get_converted_data(user_units=user_units)
            if isinstance(converted, dict):
                unit = converted.get('unit') or converted.get('units')
        except Exception:
            converted = None

        if unit is None:
            data = measurement.data or {}
            unit = data.get('unit') or data.get('original_unit')

        return FlightEstimationService._to_float(numeric_value), unit

    @staticmethod
    def _convert_value(
        value: Optional[float],
        from_unit: Optional[str],
        to_unit: Optional[str],
    ) -> Optional[float]:
        if value is None or not to_unit:
            return value
        if not from_unit or from_unit == to_unit:
            return value
        try:
            return FlightEstimationService._to_float(convert_unit(value, from_unit, to_unit))
        except Exception:
            return FlightEstimationService._to_float(value)

    @staticmethod
    def _resolve_user_units(user_units: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        if user_units is not None:
            return user_units
        default_units = FlightEstimationService._default_unit_preferences()
        if default_units:
            return copy.deepcopy(default_units)
        return None

    @staticmethod
    @lru_cache(maxsize=1)
    def _default_unit_preferences() -> Dict[str, Any]:
        try:
            from core.configuration.models import AdminConfig

            config = AdminConfig.objects.filter(name='Unit Config').first()
            if config and isinstance(getattr(config, 'settings', None), dict):
                unit_preferences = config.settings.get('unit_preferences')
                if isinstance(unit_preferences, dict):
                    return unit_preferences
        except Exception:
            pass
        return {}

