"""
Surveillance Dashboard View
Provides API endpoints for surveillance dashboard statistics.
"""

import logging
from typing import Optional
from django.http import HttpRequest
from ninja_extra import api_controller, route

from core.api.v1.auth import CustomJWTAuth
from core.common.base_response import BaseResponse
from core.role.permission import path_permission
from common.constant import MESSAGE_ENUM, get_message
from surveillance.services.surveillance_dashboard_service import SurveillanceDashboardService

logger = logging.getLogger(__name__)


@api_controller("/surveillance-dashboard", tags=["Surveillance Dashboard"])
class SurveillanceDashboardController:
    """Surveillance Dashboard API Controller."""

    @staticmethod
    def _bypass_universal_cache(request: HttpRequest) -> None:
        """
        Bypass universal cache middleware for endpoints that must return real-time data.

        Universal cache is not safe for data sourced from external files/systems because
        it cannot be reliably invalidated when those external sources change.
        """
        # UniversalOptimizer.should_cache_request() checks for header `X-No-Cache: true`
        request.META["HTTP_X_NO_CACHE"] = "true"

    @route.get("/drone-status-overview", auth=CustomJWTAuth())
    @path_permission("read", path_override="/surveillance-dashboard")
    def get_drone_status_overview(self, request: HttpRequest):
        """
        Get drone status overview statistics.
        
        Returns counts for:
        - Active: Drones with status 'available' or 'operational'
        - On Mission: Drones with status 'on_mission'
        - Warning: Drones with status 'warning'
        - Inactive: Drones with status 'inactive'
        
        Performance optimized with single aggregation query.
        
        Returns:
            BaseResponse with drone status counts
        """
        # Always fetch fresh data (no universal cache)
        self._bypass_universal_cache(request)
        try:
            data = SurveillanceDashboardService.get_drone_status_overview()
            
            return BaseResponse(
                status_code=200,
                success=True,
                message=get_message(MESSAGE_ENUM.GET_DRONE_STATUS_OVERVIEW_SUCCESS),
                data=data,
            )
        except Exception as exc:
            logger.exception("Error getting drone status overview: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.UNEXPECTED_ERROR),
                data=None,
            )

    @route.get("/daily-profile-overview", auth=CustomJWTAuth())
    @path_permission("read", path_override="/surveillance-dashboard")
    def get_daily_profile_overview(self, request: HttpRequest, date: Optional[str] = None):
        """
        Get daily surveillance profile overview statistics.
        
        Args:
            date: Optional UTC datetime string in ISO 8601 format (e.g., '2025-12-08T17:00:00+00:00')
                  or date string in format 'YYYY-MM-DD' or 'MM-DD-YYYY'.
                  UTC datetime will be converted to system timezone before extracting date.
                  If not provided, uses today's date in system timezone.
        
        Returns counts for:
        - Total: Total profiles for the selected date
        - Completed: Profiles with status 'completed'
        - Processing: Profiles with status 'in_progress', 'approved', or 'pending_device_check'
        
        Performance optimized with date filtering and aggregation.
        
        Returns:
            BaseResponse with profile counts and date
        """
        # Always fetch fresh data (no universal cache)
        self._bypass_universal_cache(request)
        try:
            # Get date from query parameter or use today
            selected_date = date or request.GET.get('date')
            
            data = SurveillanceDashboardService.get_daily_profile_overview(
                selected_date=selected_date
            )
            
            return BaseResponse(
                status_code=200,
                success=True,
                message=get_message(MESSAGE_ENUM.GET_DAILY_PROFILE_OVERVIEW_SUCCESS),
                data=data,
            )
        except Exception as exc:
            logger.exception("Error getting daily profile overview: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.UNEXPECTED_ERROR),
                data=None,
            )

    @route.get("/abnormal-signs-overview", auth=CustomJWTAuth())
    @path_permission("read", path_override="/surveillance-dashboard")
    def get_abnormal_signs_overview(self, request: HttpRequest, start_date: Optional[str] = None, end_date: Optional[str] = None):
        """
        Get abnormal signs overview statistics from detection JSON files.
        
        Args:
            start_date: UTC datetime string in ISO 8601 format (e.g., '2025-07-15T00:00:00+00:00')
            end_date: UTC datetime string in ISO 8601 format (e.g., '2025-07-18T23:59:59+00:00')
        
        Returns counts for:
        - fire_smoke: Fire and smoke detections
        - animals: Animal detections
        - human: Human/person detections
        - vehicle: Vehicle detections
        - anomaly: Anomaly detections
        
        Performance optimized with concurrent file reading and Counter-based aggregation.
        
        Returns:
            BaseResponse with detection counts by category
        """
        # Always fetch fresh data (no universal cache)
        self._bypass_universal_cache(request)
        try:
            data = SurveillanceDashboardService.get_abnormal_signs_overview(
                start_date=start_date,
                end_date=end_date
            )
            
            return BaseResponse(
                status_code=200,
                success=True,
                message=get_message(MESSAGE_ENUM.GET_ABNORMAL_SIGNS_OVERVIEW_SUCCESS),
                data=data,
            )
        except Exception as exc:
            logger.exception("Error getting abnormal signs overview: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.UNEXPECTED_ERROR),
                data=None,
            )

    @route.get("/abnormal-signs-messages", auth=CustomJWTAuth())
    @path_permission("read", path_override="/surveillance-dashboard")
    def get_abnormal_signs_messages(
        self, 
        request: HttpRequest, 
        start_date: str, 
        end_date: str,
        limit: Optional[int] = 100,
        page: Optional[int] = 1,
        page_size: Optional[int] = 10
    ):
        """
        Get detailed detection messages from detection JSON files with pagination.
        
        This API is separated from overview API to optimize performance.
        Uses thread lock to prevent concurrent execution and avoid server crash.
        Optimized with pagination and batch processing for large datasets.
        
        **IMPORTANT: This API always fetches fresh data and bypasses universal cache middleware.**
        - Universal cache middleware is bypassed via X-No-Cache header and bypass pattern
        - Always returns the latest detection data from files
        - Processes synchronously with pagination (no background processing needed)
        
        **Realtime Socket Integration:**
        - Socket should push new messages directly to clients
        - API used for initial load/pagination with fresh data
        - No cache ensures real-time data accuracy
        
        Args:
            start_date: UTC datetime string in ISO 8601 format (e.g., '2025-07-15T00:00:00+00:00')
            end_date: UTC datetime string in ISO 8601 format (e.g., '2025-07-18T23:59:59+00:00')
            limit: Maximum number of messages to fetch (default: 100, max recommended: 500)
            page: Page number for pagination (default: 1, 1-indexed)
            page_size: Number of messages per page (default: 10, max: 100)
        
        Returns:
            BaseResponse with paginated list of detection messages, pagination info, and status
        """
        # Bypass universal cache middleware by setting header
        # This ensures the API always fetches fresh data
        self._bypass_universal_cache(request)
        
        try:
            # Validate and limit parameters
            if limit is None:
                limit = 100
            limit = min(max(1, limit), 500)  # Between 1 and 500
            
            if page is None:
                page = 1
            page = max(1, page)
            
            if page_size is None:
                page_size = 10
            page_size = min(max(1, page_size), 100)  # Between 1 and 100
            
            result = SurveillanceDashboardService.get_abnormal_signs_messages(
                start_date=start_date,
                end_date=end_date,
                limit=limit,
                page=page,
                page_size=page_size
            )
            return BaseResponse(
                status_code=200,
                success=True,
                message=get_message(MESSAGE_ENUM.GET_ABNORMAL_SIGNS_MESSAGES_SUCCESS),
                data={
                    "messages": result.get("messages", []),
                    "total": result.get("total", 0),
                    "page": result.get("page", page),
                    "page_size": result.get("page_size", page_size),
                    "total_pages": result.get("total_pages", 0),
                    "status": result.get("status", "unknown"),
                    "active_profiles": result.get("active_profiles", []),
                },
            )
        except Exception as exc:
            logger.exception("Error getting abnormal signs messages: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.UNEXPECTED_ERROR),
                data=None,
            )

    @route.get("/today-region-drones", auth=CustomJWTAuth())
    @path_permission("read", path_override="/surveillance-dashboard")
    def get_today_region_drones(
        self, 
        request: HttpRequest,
        page: Optional[int] = 1,
        page_size: Optional[int] = 4
    ):
        """
        Get regions that need surveillance today with their missions and drones.
        
        Args:
            page: Page number for pagination (default: 1, 1-indexed)
            page_size: Number of regions per page (default: 4, max: 100)
        
        Returns:
            BaseResponse with paginated list of regions, pagination info
        """
        try:
            self._bypass_universal_cache(request)
            
            # Validate and normalize pagination parameters
            if page is None:
                page = 1
            page = max(1, page)
            
            if page_size is None:
                page_size = 4
            page_size = min(max(1, page_size), 100)  # Between 1 and 100
            
            result = SurveillanceDashboardService.get_today_regions_with_drones(
                page=page,
                page_size=page_size
            )

            return BaseResponse(
                status_code=200,
                success=True,
                message=get_message(MESSAGE_ENUM.GET_TODAY_REGION_DRONES_SUCCESS),
                data={
                    "regions": result.get("items", []),
                    "total": result.get("total", 0),
                    "page": result.get("page", page),
                    "page_size": result.get("page_size", page_size),
                    "total_pages": result.get("total_pages", 0),
                },
            )
        except Exception as exc:
            logger.exception("Error getting today region drones: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.UNEXPECTED_ERROR),
                data=None,
            )

    @route.get("/today-profiles-polygon", auth=CustomJWTAuth())
    @path_permission("read", path_override="/surveillance-dashboard")
    def get_today_profiles_polygon(self, request: HttpRequest):
        """
        Get polygon data for all surveillance profiles starting today.
        
        Returns polygon data for each profile including:
        - Profile information (id, name, code, color_code)
        - Mission information (id, is_line_mission)
        - Polygon coordinates (either from polygon field or waypoints for line missions)
        - Status information
        
        Performance optimized with select_related and prefetch_related.
        
        Returns:
            BaseResponse with list of profile polygon data
        """
        try:
            data = SurveillanceDashboardService.get_today_profiles_polygon()
            
            return BaseResponse(
                status_code=200,
                success=True,
                message=get_message(MESSAGE_ENUM.GET_TODAY_PROFILES_POLYGON_SUCCESS),
                data={"profiles": data},
            )
        except Exception as exc:
            logger.exception("Error getting today profiles polygon: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.UNEXPECTED_ERROR),
                data=None,
            )

    @route.get("/weather-setting", auth=CustomJWTAuth())
    @path_permission("read", path_override="/surveillance-dashboard")
    def get_weather_setting(self, request: HttpRequest):
        # Always fetch fresh data (no universal cache)
        self._bypass_universal_cache(request)
        try:
            weather_setting = SurveillanceDashboardService.get_weather_setting(request)
            return BaseResponse(
                status_code=200,
                success=True,
                message=get_message(MESSAGE_ENUM.GET_WEATHER_SETTING_SUCCESS),
                data=weather_setting,
            )
        except Exception as exc:
            logger.exception("Error getting weather setting: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.UNEXPECTED_ERROR),
                data=None,
            )
       