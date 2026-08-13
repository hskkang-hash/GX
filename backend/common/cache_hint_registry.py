"""
Centralized path -> model hint registry for universal cache keys.
Keep this list updated when new API endpoints are added.
"""
from __future__ import annotations

from typing import Dict, Iterable, Tuple, List


PATH_HINT_REGISTRY: Dict[str, str] = {
    # Terminals
    "terminals/routes": "route",
    "terminals/terminal-types": "terminaltype",
    "terminals/location-types": "locationtype",
    "terminals/docking-stations": "terminal",
    "terminals/infrastructures": "terminal",
    "terminals/delivery-hubs": "deliveryhub",
    "terminals/functions": "function",
    "terminals/qground-control": "route",
    "terminals/days-of-week": "dayofweek",
    # Devices
    "devices/devices-management": "device",
    "devices/cameras": "camera",
    "devices/imus": "imu",
    "devices/protocols": "protocol",
    "devices/packaging-specifications": "packagingspecification",
    "devices/battery-types": "batterytype",
    "devices/motor-types": "motortype",
    "devices/image-stabilizations": "imagestabilization",
    "devices/gnss-systems": "gnsssystem",
    "devices/libraries-management": "library",
    # Orders
    "orders/order": "order",
    "orders/package": "package",
    "orders/delivery-option": "deliveryoption",
    "orders/banks": "bank",
    "orders/pickup-locations": "terminal",
    "orders/external-order-statuses": "externalorderstatus",
    "orders/order-status-mappings": "orderstatusmapping",
    "orders/item-types": "itemtype",
    "orders/payment-methods": "paymentmethod",
    # Delivery
    "delivery/verification": "deliveryoperation",
    "delivery/processing": "deliveryoperation",
    "delivery/returned": "deliveryoperation",
    "delivery/completed": "deliveryoperation",
    "delivery/cancelled": "deliveryoperation",
    "delivery/delivery": "deliveryoperation",
    "delivery/delivery-report": "deliveryoperation",
    "delivery/drone-monitoring": "drone",
    "delivery/order-confirmation": "order",
    "delivery/etri-integration": "deliveryoperation",
    "delivery/etri-mock": "deliveryoperation",
    # Surveillance
    "surveillance/surveillance-profiles": "surveillanceprofile",
    "surveillance/survey-missions": "surveymission",
    "surveillance/video-analysis": "videoanalysis",
    "surveillance/surveillance-dashboard": "surveillanceprofile",
    # Handover
    "handover/handover/shift": "handovershift",
    "handover/handover/management": "handovermanagement",
    "handover/handover/content": "handovercontent",
    "handover/handover/notice": "handovernotice",
    "handover/handover/notice-comment": "handovernoticecomment",
    # Operational Data
    "operational-data/operational-data": "operationaldata",
    "operational-data/operational-notice": "operationalnotice",
    # Stream monitors
    "stream-monitors/stream-monitors": "streammonitor",
    "stream-monitors/drawing": "drawingelement",
    # Report template / print / checklist
    "report-template": "reporttemplate",
    "print-format/print-formats": "printformat",
    "checklist-setting": "checklistsetting",
    "checklist-setting/categories": "checklistsettingcategory",
    # Others
    "flight-log/flight-log": "flightlog",
    "task-status/task-status": "taskstatus",
    "media-data": "mediadata",
    "dashboard/dashboard": "dashboard",
    "partner/api/partners": "partner",
    "partner/partner-callback-mockup": "partner",
    "third-api/third-party-integration": "thirdparty",
    "third-api/api-key-management": "apikey",
    "dronehw/drone-communication-management": "drone",
    "dronehw/group-management": "usergroup",
    "operation-settings/operation-settings": "operationsettings",
    "operation-settings/menu-integration": "menuintegration",
    "operation-settings/delivery": "deliveryoperation",
}


def get_path_hint_registry() -> Iterable[Tuple[str, str]]:
    """Return registry entries sorted by longest path first."""
    return sorted(PATH_HINT_REGISTRY.items(), key=lambda item: len(item[0]), reverse=True)


def get_model_hint_aliases(model_hint: str) -> List[str]:
    """Return all path-based hints mapped to a model hint."""
    if not model_hint:
        return []
    hint_lower = model_hint.lower()
    aliases = {hint_lower}
    for _, mapped in PATH_HINT_REGISTRY.items():
        if mapped == hint_lower:
            aliases.add(mapped)
    return sorted(aliases)
