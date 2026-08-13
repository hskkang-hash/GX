from datetime import timedelta, datetime, date, timezone as dt_timezone
from django.contrib.postgres.aggregates import ArrayAgg
from django.utils import timezone
from terminals.services import terminal_service
from flight_log.services.flight_log_service import FlightLogService
from delivery.services.processing_service import ProcessingService
from devices.models import Device, DimensionsAndWeight, Measurement
from terminals.models import Terminal
from delivery.models import DeliveryOperation
from django.db.models import Count, Case, When, Value, CharField, IntegerField
from orders.models import Order, OrderItem, OrderItemType
from dashboard.models import Dashboard, DashboardPanel, WeatherSetting
from dashboard.shemas.schemas_djantic_out import DashboardOutSchema, DashboardWithoutWeatherOutSchema
from django.contrib.contenttypes.models import ContentType
from django.db.models import OuterRef, F, Subquery
from django.db.models.expressions import RawSQL
from django.db.models.functions import Concat, Coalesce, ExtractMonth
from django.db import transaction
from core.middleware.refresh_token import get_current_request
from core.user.models import CoreUser
from core.configuration.models import AdminConfig

MONTH_MAP = {
    1: "January",
    2: "February",
    3: "March",
    4: "April",
    5: "May",
    6: "June",
    7: "July",
    8: "August",
    9: "September",
    10: "October",
    11: "November",
    12: "December",
}

MONTH_MAP_KO = {
    1: "1월",
    2: "2월",
    3: "3월",
    4: "4월",
    5: "5월",
    6: "6월",
    7: "7월",
    8: "8월",
    9: "9월",
    10: "10월",
    11: "11월",
    12: "12월",
}
MONTH_MAP_TH = {
    1: "มกราคม",
    2: "กุมภาพันธ์",
    3: "มีนาคม",
    4: "เมษายน",
    5: "พฤษภาคม",
    6: "มิถุนายน",
    7: "กรกฎาคม",
    8: "สิงหาคม",
    9: "กันยายน",
    10: "ตุลาคม",
    11: "พฤศจิกายน",
    12: "ธันวาคม",
}
class DashboardRepository:
    @staticmethod
    def _resolve_user_or_system_timezone():
        """
        Resolve timezone used for date calculations in dashboards.

        Rule:
        - Use `request.user.timezone` if set.
        - Otherwise, use timezone from `AdminConfig(name="system")`.
        - Input datetimes are assumed to be UTC.
        """
        req = None
        try:
            req = get_current_request()
        except Exception:
            req = None

        # 1) User timezone
        try:
            user = getattr(req, "user", None) if req is not None else None
            user_tz = getattr(user, "timezone", None) if user is not None else None
            if user_tz is not None:
                code = getattr(user_tz, "code", None)
                if code:
                    try:
                        from zoneinfo import ZoneInfo
                        return ZoneInfo(str(code).strip())
                    except Exception:
                        pass
                offset = getattr(user_tz, "offset", None)
                if offset is not None:
                    offset_int = int(offset)
                    # DB may store offset as hours (+7) or minutes (+420)
                    if abs(offset_int) <= 24:
                        return dt_timezone(timedelta(hours=offset_int))
                    return dt_timezone(timedelta(minutes=offset_int))
        except Exception:
            pass

        # 2) System timezone from AdminConfig
        try:
            config = AdminConfig.objects.filter(name="System", is_active=True).values("settings").first()
            settings_data = config["settings"] if config and isinstance(config.get("settings"), dict) else {}
            tz_value = settings_data.get("timezone") or settings_data.get("time_zone") or settings_data.get("tz")
            if isinstance(tz_value, dict):
                tz_value = tz_value.get("code") or tz_value.get("value")
            if isinstance(tz_value, str) and tz_value.strip():
                try:
                    from zoneinfo import ZoneInfo
                    return ZoneInfo(tz_value.strip())
                except Exception:
                    if tz_value.strip().upper() == "UTC":
                        return dt_timezone.utc
            if isinstance(tz_value, (int, float)):
                tz_int = int(tz_value)
                if abs(tz_int) <= 24:
                    return dt_timezone(timedelta(hours=tz_int))
                return dt_timezone(timedelta(minutes=tz_int))
        except Exception:
            pass

        return timezone.get_current_timezone()

    @staticmethod
    def get_dashboard_by_code(dashboard_code: str) -> Dashboard:
        # Tối ưu: prefetch panels để tránh N+1 queries trong from_queryset
        return Dashboard.objects.prefetch_related('panels').filter(code=dashboard_code).first()
    
    @staticmethod
    def get_dashboard_by_id(dashboard_id: int) -> Dashboard:
        return Dashboard.objects.get(id=dashboard_id)

    @staticmethod
    def refresh_delivery_dashboard_data(request=None, user_latitude=None, user_longitude=None, location_source=None, location_accuracy=None, user_country=None, user_city=None, user_ip=None):
        # cache request + user
        req = get_current_request()
        user = req.user
        language = user.language.code if getattr(user, "language", None) else "en"

        # get or create dashboard
        dashboard = DashboardRepository.get_dashboard_by_code("delivery_dashboard")
        if not dashboard:
            dashboard = Dashboard.objects.create(
                name="Delivery Dashboard",
                code="delivery_dashboard"
            )

        # base queryset used in many places
        ops_qs = DeliveryOperation.objects.filter(another_info__etri__isnull=False)

        # total once
        total_ops = ops_qs.aggregate(total=Count("id"))["total"] or 0

        # -------------------------
        # 1) status counts in ONE query
        # -------------------------
        status_counts_qs = ops_qs.values("current_status__code").annotate(total=Count("id"))
        sc = {row["current_status__code"]: row["total"] for row in status_counts_qs}
        received_order_count = sc.get("unverified_order", 0) + sc.get("verified_order", 0)
        pending_shipment_order_count = sc.get("select_route_processing", 0) + sc.get("select_drone_processing", 0)
        in_transit_order_count = sc.get("in_transit_processing", 0)
        shipped_order_count = sc.get("completed_order", 0) + sc.get("arrived_order", 0)
        delivery_cancelled_order_count = sum(sc.get(k, 0) for k in ["cancelled", "overdue_order", "returned_order", "processed_order", "order_pending_returned", "order_due_for_returned"])
        receipt_cancelled_order_count = sc.get("receipt_cancelled", 0)

        undelivered_order_count = pending_shipment_order_count + in_transit_order_count
        completed_order_count = shipped_order_count
        scheduled_order_count = received_order_count
        if total_ops > 0 and shipped_order_count > 0:
            undelivered_completed_scheduled_order_percentage = round(shipped_order_count / total_ops * 100, 1)
        else:
            undelivered_completed_scheduled_order_percentage = 0

        # -------------------------
        # 2) monthly counts (last 3 months) — single query using ExtractMonth
        # -------------------------
        last_three_months = timezone.now() - timedelta(days=90)
        monthly_qs = (
            ops_qs.filter(created_on__gte=last_three_months)
            .annotate(month=ExtractMonth("created_on"))
            .values("month")
            .annotate(count=Count("id"))
        )
        # convert to list of dicts similar to original
        last_three_months_order_count = list(monthly_qs.order_by("month"))

        # -------------------------
        # 3) today / yesterday / today's status counts — combine when possible
        # -------------------------
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        created_date_counts = (
            ops_qs.filter(created_on__date__in=[today, yesterday])
            .values("created_on__date")
            .annotate(total=Count("id"))
        )
        created_map = {row["created_on__date"]: row["total"] for row in created_date_counts}
        today_order_count = created_map.get(today, 0)
        yesterday_order_count = created_map.get(yesterday, 0)

        # today's modified status counts (combined)
        today_mod_qs = ops_qs.filter(modified_on__date=today)
        today_status_counts = (
            today_mod_qs.values("current_status__code").annotate(total=Count("id"))
        )
        tsc = {r["current_status__code"]: r["total"] for r in today_status_counts}
        today_rejected_order_count = sum(tsc.get(k, 0) for k in ["cancelled", "receipt_cancelled", "overdue_order", "returned_order", "processed_order", "order_pending_returned", "order_due_for_returned"])
        today_completed_order_count = tsc.get("completed_order", 0) + tsc.get("arrived_order", 0)
        today_scheduled_order_count = tsc.get("unverified_order", 0)

        # -------------------------
        # 4) item type counts — single query + fetch translations in-memory
        # -------------------------
        # Get all item types once (for names/translations)
        item_types = list(OrderItemType.objects.all().order_by("id"))
        # counts per code
        item_type_counts_qs = (
            OrderItem.objects
            .filter(order__delivery_operation__another_info__etri__isnull=False)
            .values("item_type__code")
            .annotate(count=Count("id"))
        )
        item_type_count_map = {r["item_type__code"]: r["count"] for r in item_type_counts_qs}
        item_type_codes = [it.code for it in item_types]
        item_type_counts_dict = {
            it.code: {
                "name": it.get_translation("name", language),
                "count": item_type_count_map.get(it.code, 0)
            } for it in item_types
        }

        # -------------------------
        # 5) region counts (avoid loop) — one query
        # -------------------------
        region_qs = (
            Order.objects
            .filter(delivery_operation__another_info__etri__isnull=False)
            .values("recipient_address__city")
            .annotate(count=Count("id"))
        )
        region_order_counts = [
            {"region": r["recipient_address__city"], "count": r["count"]}
            for r in region_qs if r["recipient_address__city"]
        ]

        # -------------------------
        # 6) weight counts (kept as annotate + Case)
        # -------------------------
        weight_counts_qs = (
            OrderItem.objects
            .filter(weight__value__isnull=False, order__delivery_operation__another_info__etri__isnull=False)
            .annotate(
                weight_category=Case(
                    When(weight__value__lt=2, then=Value("0-2kg")),
                    When(weight__value__gte=2, weight__value__lt=5, then=Value("2-5kg")),
                    When(weight__value__gte=5, then=Value(">5kg")),
                    default=Value("No weight"),
                    output_field=CharField()
                )
            )
            .values("weight_category")
            .annotate(count=Count("id"))
        )
        weight_counts = list(weight_counts_qs)

        # -------------------------
        # 7) terminals / docking station counts (external helper left as-is)
        # -------------------------
        delivery_hub_count = Terminal.objects.filter(terminal_types__code="DELIVERY_HUB").distinct().count()
        docking_station_count = terminal_service.get_docking_station_terminals(search_route=False).count()
        delivery_point_count = Terminal.objects.filter(terminal_types__code__in=["INFRASTRUCTURE"]).distinct().count() + docking_station_count

        # -------------------------
        # 8) user signup counts — simplified to COUNT-only queries (no heavy annotations)
        # -------------------------
        # determine user role quick
        roles_codes = list(user.roles.values_list("code", flat=True)) if hasattr(user, "roles") else []
        is_superuser_like = user.is_superuser or ("superuser" in roles_codes)

        if is_superuser_like:
            pending_approval_signup_count = CoreUser._base_manager.filter(is_active=False, is_rejected=False, deleted=None).count()
            completed_signup_count = CoreUser.get_complete_user_queryset().filter(deleted=None, partner_profile__isnull=True).count()
            rejected_signup_count = CoreUser._base_manager.filter(is_rejected=True, deleted=None).count()
        elif getattr(user, "userprofilelink", None) and getattr(user.userprofilelink, "group", None):
            user_group_id = user.userprofilelink.group.id
            pending_approval_signup_count = CoreUser.objects.filter(is_active=False, is_rejected=False, userprofilelink__group_id=user_group_id, deleted=None).count()
            completed_signup_count = CoreUser.get_complete_user_queryset(user_group_id=user_group_id).filter(deleted=None, partner_profile__isnull=True).count()
            rejected_signup_count = CoreUser._base_manager.filter(is_rejected=True, userprofilelink__group_id=user_group_id, deleted=None).count()
        else:
            pending_approval_signup_count = completed_signup_count = rejected_signup_count = 0

        # -------------------------
        # 9) clear existing panels + bulk create new panels
        # -------------------------
        # Build panels data (reuse same JSON structure as original)
        panels_to_create = []

        # Helper to add a panel
        def add_panel(title, ptype, pdata, pconfig=None):
            panels_to_create.append(DashboardPanel(
                dashboard=dashboard,
                panel_title=title,
                panel_type=ptype,
                panel_config=pconfig or {},
                panel_data=pdata
            ))

        # Panel 1
        panel1_data = {"data": [
            {"label": "Receipt Completed", "value": received_order_count, "color": {"light": "#2EB4FF", "dark": "#2EB4FF"}},
            {"label": "Waiting for Delivery", "value": pending_shipment_order_count, "color": {"light": "#FFD530", "dark": "#FFD530"}},
            {"label": "In Delivery", "value": in_transit_order_count, "color": {"light": "#FA9C2A", "dark": "#FA9C2A"}},
            {"label": "Delivery Completed", "value": shipped_order_count, "color": {"light": "#41D078", "dark": "#41D078"}},
            {"label": "Delivery Cancelled", "value": delivery_cancelled_order_count, "color": {"light": "#FD3F31", "dark": "#FD3F31"}},
            {"label": "Receipt Cancelled", "value": receipt_cancelled_order_count, "color": {"light": "#E63886", "dark": "#E63886"}}
        ]}
        add_panel("Delivery Progress", "donut_chart", panel1_data, {"type": "donut", "field": "series"})

        # Panel 2
        panel2_data = {"data": [
            {"label": "Receipt Completed", "value": received_order_count, "color": {"light": "#2EB4FF", "dark": "#2EB4FF"}},
            {"label": "Waiting for Delivery", "value": pending_shipment_order_count, "color": {"light": "#FFD530", "dark": "#FFD530"}}
        ]}
        add_panel("Receipt Completed vs Waiting for Delivery", "metric", panel2_data, {"icon": "bell"})

        # Panel 3
        panel3_data = {"data": [
            {"label": "In Delivery", "value": in_transit_order_count, "color": {"light": "#FA9C2A", "dark": "#FA9C2A"}},
            {"label": "Delivery Completed", "value": shipped_order_count, "color": {"light": "#41D078", "dark": "#41D078"}}
        ]}
        add_panel("In Delivery vs Delivery Completed", "metric", panel3_data, {"icon": "calendar"})

        # Panel 4
        panel4_data = {"data": [
            {"label": "Delivery Cancelled", "value": delivery_cancelled_order_count, "color": {"light": "#FD3F31", "dark": "#FD3F31"}},
            {"label": "Receipt Cancelled", "value": receipt_cancelled_order_count, "color": {"light": "#E63886", "dark": "#E63886"}}
        ]}
        add_panel("Cancellation", "metric", panel4_data, {"icon": "clipboard-cancel"})

        # Panel 5 - Monthly
        def month_label(m):
            if language == "ko":
                return MONTH_MAP_KO.get(m, str(m))
            if language == "th":
                return MONTH_MAP_TH.get(m, str(m))
            return MONTH_MAP.get(m, str(m))
        panel5_data = {"data": [
            {"label": month_label(m['month']), "value": m['count'], "color": {"light": "#42bbfe", "dark": "#42bbfe"}}
            for m in last_three_months_order_count
        ]}
        add_panel("Monthly Delivery Statistics", "bar_chart", panel5_data, {"type": "bar", "x_axis": "month", "y_axis": "deliveries"})

        # Panel 6 - Item types
        panel6_data = {"data": [
            {"label": item_type_counts_dict.get(code, {}).get("name", code), "value": item_type_counts_dict.get(code, {}).get("count", 0), "color": {"light": "#42bbfe", "dark": "#42bbfe"}}
            for code in item_type_codes
        ]}
        add_panel("Delivered Items", "item_metric", panel6_data, {"icon": "package", "columns": ["item_type", "count"]})

        # Panel 7 - Regions
        panel7_data = {"data": [
            {"label": r["region"], "value": r["count"], "color": {"light": "#6e45e3", "dark": "#6e45e3"}}
            for r in region_order_counts
        ]}
        add_panel("Regional Order Stats", "mono_color_metric", panel7_data, {"icon": "building", "columns": ["region", "count"]})

        # Panel 8 - Weight
        panel8_data = {"data": [
            {"label": w["weight_category"], "value": w["count"], "color": {"light": "#6e45e3", "dark": "#6e45e3"}}
            for w in weight_counts
        ]}
        add_panel("Order Stats by Weight", "mono_color_metric", panel8_data, {"icon": "weight", "columns": ["weight_range", "count"]})

        # Panel 9 - Last mile
        panel9_data = {"data": [
            {"label": "Completed", "value": completed_order_count, "color": {"light": "#1EA1EB", "dark": "#1EA1EB"}},
            {"label": "Undelivered", "value": undelivered_order_count, "color": {"light": "#FF9F46", "dark": "#FF9F46"}},
            {"label": "Scheduled", "value": scheduled_order_count, "color": {"light": "#CAD8EA", "dark": "#CAD8EA"}}
        ], "percentage": undelivered_completed_scheduled_order_percentage}
        add_panel("Last Mile Delivery Progress", "donut_chart", panel9_data, {"type": "donut", "field": "series"})

        # Panel 10
        panel10_data = {"data": [
            {"label": "Today", "value": today_order_count, "date": today.strftime("%m/%d"), "color": {"light": "#1EA1EB", "dark": "#1EA1EB"}},
            {"label": "Yesterday", "value": yesterday_order_count, "date": yesterday.strftime("%m/%d"), "color": {"light": "#5E54CE", "dark": "#5E54CE"}}
        ]}
        add_panel("Delivery Booking Status", "metric", panel10_data, {"icon": "bell"})

        # Panel 11
        panel11_data = {"data": [
            {"label": "Rejected", "value": today_rejected_order_count, "date": today.strftime("%m/%d"), "color": {"light": "#E5563C", "dark": "#E5563C"}},
            {"label": "Completed", "value": today_completed_order_count, "date": today.strftime("%m/%d"), "color": {"light": "#1EA1EB", "dark": "#1EA1EB"}}
        ]}
        add_panel("Delivery Approval", "metric", panel11_data, {"icon": "clipboard-cancel"})

        # Panel 12
        panel12_data = {"data": [
            {"label": "Scheduled", "value": today_scheduled_order_count, "date": today.strftime("%m/%d"), "color": {"light": "#F8D037", "dark": "#F8D037"}},
            {"label": "Completed", "value": today_completed_order_count, "date": today.strftime("%m/%d"), "color": {"light": "#1EA1EB", "dark": "#1EA1EB"}}
        ]}
        add_panel("Delivery Status", "metric", panel12_data, {"icon": "calendar"})

        # Panels 13-16 (tri items) - kept with zeros as original
        panel13_data = {"data": [{"label": "≤25kg", "value": 0, "icon": "s-drone"}, {"label": "≤40kg", "value": 0, "icon": "m-drone"}, {"label": "≤40kg", "value": 0, "icon": "robot"}]}
        add_panel("Number of Drones/Robots", "tri_items", panel13_data)

        panel14_data = {"data": [{"label": "Delivery Hub", "value": delivery_hub_count, "icon": "delivery-hub"}, {"label": "Docking Station", "value": docking_station_count, "icon": "docking-station"}, {"label": "Delivery Point", "value": delivery_point_count, "icon": "delivery-point"}]}
        add_panel("Last Mile Infrastructure Status", "tri_items", panel14_data)

        panel15_data = panel13_data
        add_panel("Controlled Drones/Robots", "tri_items", panel15_data)

        panel16_data = panel13_data
        add_panel("Uncontrolled Drones/Robots", "tri_items", panel16_data)

        # Panel 17
        panel17_data = {"data": [{"label": "Drones", "count": 0, "size": 0, "color": {"light": "#1EA1EB", "dark": "#1EA1EB"}}, {"label": "Robots", "count": 0, "size": 0, "color": {"light": "#5E54CE", "dark": "#5E54CE"}}]}
        add_panel("Log Data Collection", "record", panel17_data)

        # Panel 18 - signups
        panel18_data = {"data": [
            {"label": "Pending Approval", "value": pending_approval_signup_count, "color": {"light": "#2EB4FF", "dark": "#2EB4FF"}},
            {"label": "Completed", "value": completed_signup_count, "color": {"light": "#0CBA47", "dark": "#0CBA47"}},
            {"label": "Rejected", "value": rejected_signup_count, "color": {"light": "#EB7509", "dark": "#EB7509"}}
        ]}
        add_panel("Pending Sign-ups", "metric", panel18_data, {"icon": "calendar"})

        # perform DB changes inside a transaction: delete old panels + bulk_create new ones
        with transaction.atomic():
            DashboardPanel.objects.filter(dashboard__code="delivery_dashboard").delete()
            DashboardPanel.objects.bulk_create(panels_to_create)

            # update dashboard timestamp
            dashboard.data_updated_at = timezone.now()
            dashboard.save(update_fields=["data_updated_at"])

        # format output (keep original formatting utility)
        formatted_data = DashboardOutSchema.from_queryset_with_weather(
            dashboard,
            request=request,
            user_latitude=user_latitude,
            user_longitude=user_longitude,
            location_source=location_source,
            location_accuracy=location_accuracy,
            user_country=user_country,
            user_city=user_city,
            user_ip=user_ip
        )

        return formatted_data
    @staticmethod
    def _convert_utc_to_system_timezone_date(utc_datetime):
        """
        Chuyển đổi UTC datetime sang date theo timezone của user (nếu có),
        nếu không thì theo timezone hệ thống (AdminConfig).
        
        Args:
            utc_datetime: datetime object hoặc string (UTC) hoặc date object
            
        Returns:
            date object theo timezone user/system
        """
        if utc_datetime is None:
            return None
        
        # Nếu đã là date object, trả về luôn
        if isinstance(utc_datetime, date) and not isinstance(utc_datetime, datetime):
            return utc_datetime
        
        # Nếu là string, parse thành datetime
        if isinstance(utc_datetime, str):
            try:
                # Thử parse ISO format với timezone
                if 'T' in utc_datetime or '+' in utc_datetime or utc_datetime.endswith('Z'):
                    utc_datetime = datetime.fromisoformat(utc_datetime.replace('Z', '+00:00'))
                else:
                    # Nếu chỉ là date string, parse thành date
                    return datetime.strptime(utc_datetime, '%Y-%m-%d').date()
            except (ValueError, AttributeError):
                # Fallback: thử parse các format khác
                try:
                    utc_datetime = datetime.strptime(utc_datetime, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    return None
        
        # Nếu là datetime nhưng chưa có timezone, giả định là UTC
        if isinstance(utc_datetime, datetime):
            if timezone.is_naive(utc_datetime):
                # Nếu là naive datetime, giả định là UTC
                utc_datetime = timezone.make_aware(utc_datetime, dt_timezone.utc)
            else:
                # Đảm bảo datetime là UTC
                if utc_datetime.tzinfo != dt_timezone.utc:
                    utc_datetime = utc_datetime.astimezone(dt_timezone.utc)
            
            # Chuyển đổi sang timezone của user/system
            tzinfo = DashboardRepository._resolve_user_or_system_timezone()
            local_datetime = utc_datetime.astimezone(tzinfo)
            
            # Trả về date theo timezone user/system
            return local_datetime.date()
        
        return None

    @staticmethod
    def refresh_anyang_dashboard_data(start_date=None, end_date=None):
        dashboard = DashboardRepository.get_dashboard_by_code("anyang_dashboard")
        if not dashboard:
            dashboard = Dashboard.objects.create(
                name="Anyang Dashboard",
                code="anyang_dashboard"
            )

        # Clear existing panels
        DashboardPanel.objects.filter(dashboard__code="anyang_dashboard").delete()

        if start_date is None or end_date is None:
            delivery_order_count = DeliveryOperation.objects.filter(
                current_status__code__in=["completed_order"]
            ).count()
            received_order_count = DeliveryOperation.objects.filter(
                current_status__code__in=["unverified_order", "verified_order"]
            ).count()
            cancelled_order_count = DeliveryOperation.objects.filter(
                current_status__code__in=["receipt_cancelled", "cancelled"]
            ).count()
        else:
            # Chuyển đổi UTC datetime sang date trong timezone hệ thống
            start_date_converted = DashboardRepository._convert_utc_to_system_timezone_date(start_date)
            end_date_converted = DashboardRepository._convert_utc_to_system_timezone_date(end_date)
            
            if start_date_converted is None or end_date_converted is None:
                # Nếu không parse được, fallback về logic không filter
                delivery_order_count = DeliveryOperation.objects.filter(
                    current_status__code__in=["completed_order"]
                ).count()
                received_order_count = DeliveryOperation.objects.filter(
                    current_status__code__in=["unverified_order", "verified_order"]
                ).count()
                cancelled_order_count = DeliveryOperation.objects.filter(
                    current_status__code__in=["receipt_cancelled", "cancelled"]
                ).count()
            else:
                delivery_order_count = DeliveryOperation.objects.filter(
                    current_status__code__in=["completed_order"], 
                    modified_on__date__range=(start_date_converted, end_date_converted)
                ).count()
                received_order_count = DeliveryOperation.objects.filter(
                    current_status__code__in=["unverified_order", "verified_order"],
                    modified_on__date__range=(start_date_converted, end_date_converted)
                ).count()
                cancelled_order_count = DeliveryOperation.objects.filter(
                    current_status__code__in=["receipt_cancelled", "cancelled"],
                    modified_on__date__range=(start_date_converted, end_date_converted)
                ).count()

        if DeliveryOperation.objects.count() > 0 and delivery_order_count > 0:
            completed_order_percentage = delivery_order_count / (delivery_order_count + received_order_count + cancelled_order_count) * 100
        else:
            completed_order_percentage = 0
        # rounding to 1 decimal place if undelivered_completed_scheduled_order_percentage is not integer
        completed_order_percentage = round(completed_order_percentage, 1)

        # panel 9: Donut Chart - Last Mile Delivery Progress
        panel1_data = {
            "data": [
                {
                    "label": "Received",
                    "value": received_order_count,
                    "color": {
                        "light": "#683DE2",
                        "dark": "#683DE2"
                    }
                },
                {
                    "label": "Cancelled",
                    "value": cancelled_order_count,
                    "color": {
                        "light": "#E5563C",
                        "dark": "#E5563C"
                    }
                },
                {
                    "label": "Delivered",
                    "value": delivery_order_count,
                    "color": {
                        "light": "#2EB4FF",
                        "dark": "#2EB4FF"
                    }
                }
            ],
            "percentage": completed_order_percentage
        }
        
        DashboardPanel.objects.create(
            dashboard=dashboard,
            panel_title="Overall Delivery Service Status",
            panel_type="donut_chart",
            panel_config={"type": "donut", "field": "series"},
            panel_data=panel1_data
        )

        # panel 2: Tri items - Operation Status
        delivery_hubs = Terminal.objects.filter(terminal_types__code='DELIVERY_HUB')
        delivery_hub_info = []
        for station in delivery_hubs:
            delivery_hub_info.append(DashboardRepository.get_delivery_hub_info(station))
        
        panel2_data = {
            "data": delivery_hub_info
        }   
        DashboardPanel.objects.create(
            dashboard=dashboard,
            panel_title="Operation Status",
            panel_type="tri_items",
            panel_data=panel2_data
        )
        
        # update dashboard data_updated_at
        dashboard.data_updated_at = timezone.now()
        dashboard.save()

        # Tối ưu: reload dashboard với prefetch_related để tránh N+1 queries
        dashboard = Dashboard.objects.prefetch_related('panels').filter(id=dashboard.id).first()

        # Use from_queryset_with_weather to format data with additional weather/location information
        formatted_data = DashboardWithoutWeatherOutSchema.from_queryset(
            dashboard
        )
        
        return formatted_data

    @staticmethod
    def get_linked_delivery_hubs_with_status(docking_station_id):
        """
        Get linked delivery hub terminals with name and active status
        Returns list of dictionaries with name and active status
        """
        from django.db import connection
        sql = """
        SELECT DISTINCT linked_terminal.name, linked_terminal.active
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
            WHERE rt.terminal_id = %s
        )
        AND linked_terminal.id != %s
        ORDER BY linked_terminal.name
        """
        
        with connection.cursor() as cursor:
            cursor.execute(sql, [docking_station_id, docking_station_id])
            results = cursor.fetchall()
            
        return [{'name': row[0], 'active': row[1]} for row in results]
    
    @staticmethod
    def get_linked_docking_stations_with_status(delivery_hub_id):
        """
        Get linked docking station terminals with name and active status
        Returns list of dictionaries with name and active status
        """
        from django.db import connection
        sql = """
        SELECT DISTINCT linked_terminal.name, linked_terminal.active, linked_terminal.latitude, linked_terminal.longitude
        FROM terminals_terminal linked_terminal
        INNER JOIN terminals_terminal_terminal_types linked_ttt 
            ON linked_terminal.id = linked_ttt.terminal_id
        INNER JOIN terminals_terminaltype linked_tt 
            ON linked_ttt.terminaltype_id = linked_tt.id
        INNER JOIN terminals_routeterminal linked_rt 
            ON linked_terminal.id = linked_rt.terminal_id
        WHERE linked_tt.code = 'DOCKING_STATION'
        AND linked_rt.route_id IN (
            SELECT rt.route_id
            FROM terminals_routeterminal rt
            WHERE rt.terminal_id = %s
        )
        AND linked_terminal.id != %s
        ORDER BY linked_terminal.name
        """
        
        with connection.cursor() as cursor:
            cursor.execute(sql, [delivery_hub_id, delivery_hub_id])
            results = cursor.fetchall()
            
        return [{'name': row[0], 'active': row[1], 'latitude': row[2], 'longitude': row[3]} for row in results]

    @staticmethod
    def get_delivery_hub_info(delivery_hub):
        # Use the new method to get linked terminals with name and active status
        linked_terminals_info = DashboardRepository.get_linked_docking_stations_with_status(delivery_hub.id)
        
        # Single subquery for payload capacity (value + unit)
        DIMENSIONS_CT_ID = ContentType.objects.get_for_model(DimensionsAndWeight).id
        payload_capacity_subq = (
            Measurement.objects
            .filter(
                content_type_id=DIMENSIONS_CT_ID,
                object_id=OuterRef('dimensions_and_weight__id'),
                measurement_type='payload_capacity'
            )
            .annotate(
                full_capacity=Concat(
                    F('data__value'),
                    Value(' '),
                    RawSQL("(data ->> 'unit')", []),
                    output_field=CharField()
                )
            )
            .values('full_capacity')[:1]
        )
        # get all devices that are in that terminal based on device_type
        devices = Device.objects.filter(terminal=delivery_hub).annotate(
            payload_capacity=Coalesce(
                Subquery(payload_capacity_subq),
                Value('N/A'),
                output_field=CharField()
            )
        )
        weight_capacity_groups = {
            "0 kg": {
                "drones": [],
                "robots": []
            }
        }
        for device in devices:
            try:
                drone_location = ProcessingService.get_drone_location_by_unique_id(device.unit_id)
            except Exception as e:
                drone_location = {'latitude': 0, 'longitude': 0}
            # get anomaly prediction
            try:
                anomaly_prediction = FlightLogService.get_flight_log_with_anomaly_prediction(device.serial_number)
            except Exception as e:
                anomaly_prediction = 0
            device_info = {
                'device': device.name,
                'id': device.id,
                'status': device.status.code if device.status else None,
                'color': device.color,
                'type': device.main_type.name,
                'location': drone_location,
                'anomaly_prediction': anomaly_prediction if anomaly_prediction else 0
            }
            weight_capacity = device.payload_capacity
            if weight_capacity == 'N/A':
                weight_capacity = '0 kg'
            if weight_capacity not in weight_capacity_groups:
                weight_capacity_groups[weight_capacity] = {
                    "drones": [],
                    "robots": []
                }
            if device.main_type.name == 'Drone' or device.main_type.name == '드론':
                weight_capacity_groups[weight_capacity]["drones"].append(device_info)
            elif device.main_type.name == 'Robot' or device.main_type.name == '항공기':
                weight_capacity_groups[weight_capacity]["robots"].append(device_info)

        # get lattitude, longtitude and name of the docking station
        docking_station_info = {
            'name': delivery_hub.name,
            'latitude': delivery_hub.latitude,
            'longitude': delivery_hub.longitude,
            'active': delivery_hub.active
        }
        
        return {
            'docking_station': docking_station_info,
            'linked_terminals': linked_terminals_info,
            'devices': weight_capacity_groups
        }

    @staticmethod
    def create_weather_setting(latitude, longitude, address, is_surveillance_dashboard=False):
        return WeatherSetting.objects.create(latitude=latitude, longitude=longitude, address=address, is_surveillance_dashboard=is_surveillance_dashboard)

    @staticmethod
    def get_devices_location():
        delivery_hubs = Terminal.objects.filter(terminal_types__code='DELIVERY_HUB')
        devices = Device.objects.filter(terminal__in=delivery_hubs, main_type__name__in=['Drone', '드론', 'Robot', '항공기']).exclude(status__code='inactive')
        devices_location = []
        for device in devices:
            try:
                drone_location = ProcessingService.get_drone_location_by_unique_id(device.unit_id)
            except Exception as e:
                drone_location = {'latitude': 0, 'longitude': 0}
            devices_location.append({
                'device': device.name,
                'id': device.id,
                'status': device.status.code if device.status else None,
                'color': device.color,
                'type': device.main_type.name,
                'location': drone_location
            })
        return devices_location

    @staticmethod
    def refresh_delivery_dashboard_data_default(request=None, user_latitude=None, user_longitude=None, location_source=None, location_accuracy=None, user_country=None, user_city=None, user_ip=None):
        dashboard = DashboardRepository.get_dashboard_by_code("delivery_dashboard")
        # if dashboard is not exist, create it
        if not dashboard:
            dashboard = Dashboard.objects.create(
                name="Delivery Dashboard",
                code="delivery_dashboard"
            )
        # Clear existing panels
        DashboardPanel.objects.filter(dashboard__code="delivery_dashboard").delete()

        # Panel 1: Donut Chart - Order Status
        panel1_data = {
            "data": [
                {
                    "label": "Received",
                    "value": 100,
                    "color": {
                        "light": "#43bcff",
                        "dark": "#43bcff"
                    }
                },
                {
                    "label": "Pending Shipment",
                    "value": 50,
                    "color": {
                        "light": "#ffda45",
                        "dark": "#ffda45"
                    }
                },
                {
                    "label": "In Transit",
                    "value": 50,
                    "color": {
                        "light": "#fba640",
                        "dark": "#fba640"
                    }
                },
                {
                    "label": "Shipped",
                    "value": 25,
                    "color": {
                        "light": "#54d586",
                        "dark": "#54d586"
                    }
                },
                {
                    "label": "Cancelled",
                    "value": 24,
                    "color": {
                        "light": "#fe5246",
                        "dark": "#fe5246"
                    }
                }
            ]
        }
        DashboardPanel.objects.create(
            dashboard=dashboard,
            panel_title="Delivery Progress",
            panel_type="donut_chart",
            panel_config={"type": "donut", "field": "series"},
            panel_data=panel1_data
        )

        # Panel 2: Metric - Received
        panel2_data = {
            "data": [
                {
                    "label": "This Month",
                    "value": 154,
                    "color": {
                        "light": "#41bbff",
                        "dark": "#41bbff"
                    }
                },
                {
                    "label": "Last Month",
                    "value": 159,
                    "color": {
                        "light": "#675ed1",
                        "dark": "#675ed1"
                    }
                }
            ]
        }
        DashboardPanel.objects.create(
            dashboard=dashboard,
            panel_title="Received",
            panel_type="metric",
            panel_config={"icon": "bell"},
            panel_data=panel2_data
        )

        # Panel 3: Metric - Completion vs Cancellation
        panel3_data = {
            "data": [
                {
                    "label": "Shipped",
                    "value": 100,
                    "color": {
                        "light": "#41bbff",
                        "dark": "#41bbff"
                    }
                },
                {
                    "label": "Cancelled",
                    "value": 41,
                    "color": {
                        "light": "#fe5246",
                        "dark": "#fe5246"
                    }
                }
            ]
        }
        DashboardPanel.objects.create(
            dashboard=dashboard,
            panel_title="Completion vs Cancellation",
            panel_type="metric",
            panel_config={"icon": "clipboard-check"},
            panel_data=panel3_data
        )
        # Panel 4: Metric - Pending Shipment vs In Transit
        panel4_data = {
            "data": [
                {
                    "label": "Pending Shipment",
                    "value": 80,
                    "color": {
                        "light": "#ffda45",
                        "dark": "#ffda45"
                    }
                },
                {
                    "label": "In Transit",
                    "value": 134,
                    "color": {
                        "light": "#fba640",
                        "dark": "#fba640"
                    }
                }
            ]
        }
        DashboardPanel.objects.create(
            dashboard=dashboard,
            panel_title="Pending Shipment vs In Transit",
            panel_type="metric",
            panel_config={"icon": "calendar"},
            panel_data=panel4_data
        )
        
        # Panel 5: Bar Chart - Monthly Delivery Stats
        panel5_data = {
            "data": [
                {
                    "label": "May",
                    "value": 56,
                    "color": {
                        "light": "#42bbfe",
                        "dark": "#42bbfe"
                    }
                },
                {
                    "label": "June",
                    "value": 64,
                    "color": {
                        "light": "#42bbfe",
                        "dark": "#42bbfe"
                    }
                },
                {
                    "label": "July",
                    "value": 76,
                    "color": {
                        "light": "#42bbfe",
                        "dark": "#42bbfe"
                    }
                }
            ]
        }
        DashboardPanel.objects.create(
            dashboard=dashboard,
            panel_title="Monthly Delivery Stats",
            panel_type="bar_chart",
            panel_config={"type": "bar", "x_axis": "month", "y_axis": "deliveries"},
            panel_data=panel5_data
        )

        # Panel 6: Key-Value - Order Stats by Item Type
        panel6_data = {
            "data": [
                {
                    "label": "Food",
                    "value": 531,
                    "color": {
                        "light": "#42bbfe",
                        "dark": "#42bbfe"
                    }
                },
                {
                    "label": "Clothing",
                    "value": 305,
                    "color": {
                        "light": "#42bbfe",
                        "dark": "#42bbfe"
                    }
                },
                {
                    "label": "Electronics",
                    "value": 363,
                    "color": {
                        "light": "#42bbfe",
                        "dark": "#42bbfe"
                    }
                },
                {
                    "label": "Documents",
                    "value": 172,
                    "color": {
                        "light": "#42bbfe",
                        "dark": "#42bbfe"
                    }
                },
                {
                    "label": "Other",
                    "value": 568,
                    "color": {
                        "light": "#42bbfe",
                        "dark": "#42bbfe"
                    }
                }
            ]
        }
        DashboardPanel.objects.create(
            dashboard=dashboard,
            panel_title="Order Stats by Item Type",
            panel_type="item_metric",
            panel_config={"icon": "package", "columns": ["item_type", "count"]},
            panel_data=panel6_data
        )

        # Panel 7: Key-Value - Regional Order Stats
        panel7_data = {
            "data": [
                {
                    "label": "Region 1",
                    "value": 100,
                    "color": {
                        "light": "#6e45e3",
                        "dark": "#6e45e3"
                    }
                },
                {
                    "label": "Region 2",
                    "value": 154,
                    "color": {
                        "light": "#6e45e3",
                        "dark": "#6e45e3"
                    }
                },
                {
                    "label": "Incheon",
                    "value": 159,
                    "color": {
                        "light": "#6e45e3",
                        "dark": "#6e45e3"
                    }
                }
            ]
        }
        DashboardPanel.objects.create(
            dashboard=dashboard,
            panel_title="Regional Order Stats",
            panel_type="mono_color_metric",
            panel_config={"icon": "building", "columns": ["region", "count"]},
            panel_data=panel7_data
        )

        # Panel 8: Key-Value - Order Stats by Weight
        panel8_data = {
            "data": [
                {
                    "label": "0-2kg",
                    "value": 100,
                    "color": {
                        "light": "#6e45e3",
                        "dark": "#6e45e3"
                    }
                },
                {
                    "label": "2-5kg",
                    "value": 154,
                    "color": {
                        "light": "#6e45e3",
                        "dark": "#6e45e3"
                    }
                },
                {
                    "label": "Over 5kg",
                    "value": 159,
                    "color": {
                        "light": "#6e45e3",
                        "dark": "#6e45e3"
                    }
                }
            ]
        }
        DashboardPanel.objects.create(
            dashboard=dashboard,
            panel_title="Order Stats by Weight",
            panel_type="mono_color_metric",
            panel_config={"icon": "weight", "columns": ["weight_range", "count"]},
            panel_data=panel8_data
        )

        # Use from_queryset_with_weather to format data with additional weather/location information
        formatted_data = DashboardOutSchema.from_queryset_with_weather(
            dashboard, 
            request=request,
            user_latitude=user_latitude,
            user_longitude=user_longitude,
            location_source=location_source,
            location_accuracy=location_accuracy,
            user_country=user_country,
            user_city=user_city,
            user_ip=user_ip
        )
        
        return formatted_data