
import os
import sys
import django
from pytz import timezone


sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from delivery.models import DeliveryStatus
from core.multilanguage.request_handlers import process_multilanguage_request, create_model_with_translations, update_model_with_translations, get_model_with_translations

DELIVERY_STATUS_LIST = [
    # verification group
    {"code": "unverified_order", "name": {
        "en": "Unverified",
        "ko": "미검증 주문"
    }, "description": {
        "en": "Order not yet verified",
        "ko": "주문이 아직 검증되지 않았습니다."
    }, "color_code": "#9C9D9D"},

    {"code": "verified_order", "name": {
        "en": "Verified",
        "ko": "검증된 주문"
    }, "description": {
        "en": "Order has been verified",
        "ko": "주문이 검증되었습니다."
    }, "color_code": "#1D9BE2"},

    # processing group
        {"code": "select_route_processing", "name": {
        "en": "Select Route",
        "ko": "라우트 선택"
    }, "description": {
        "en": "Select delivery route",
        "ko": "배송 라우트 선택"
    }, "color_code": "#1E90FF"},
    {"code": "select_drone_processing", "name": {
        "en": "Select Drone",
        "ko": "드론 선택"
    }, "description": {
        "en": "Select delivery drone",
        "ko": "배송 드론 선택"
    }, "color_code": "#4682B4"},
    {"code": "in_transit_processing", "name": {
        "en": "In Transit Processing",
        "ko": "배송 중"
    }, "description": {
        "en": "Drone is delivering the order",
        "ko": "드론이 주문을 배송 중입니다."
    }, "color_code": "#6495ED"},

    # completed group
    {"code": "arrived_order", "name": {
        "en": "Arrived",
        "ko": "도착 주문"
    }, "description": {
        "en": "Arrived at warehouse",
        "ko": "창고에 도착했습니다."
    }, "color_code": "#EB7509"},
    {"code": "completed_order", "name": {
        "en": "Completed",
        "ko": "완료 주문"
    }, "description": {
        "en": "Successfully delivered",
        "ko": "성공적으로 배송되었습니다."
    }, "color_code": "#0CBA47"},

    # return group
    {"code": "order_due_for_returned", "name": {
        "en": "Due For Return",
        "ko": "반환 주문"
    }, "description": {
        "en": "Order needs to be returned",
        "ko": "주문이 반환되어야 합니다."
    }, "color_code": "#414DAD"},
    {"code": "order_pending_returned", "name": {
        "en": "Pending Return",
        "ko": "반환 주문 대기"
    }, "description": {
        "en": "Order pending return",
        "ko": "반환 주문 대기"
    }, "color_code": "#F0C418"},
    {"code": "overdue_order", "name": {
        "en": "Overdue",
        "ko": "지연 주문"
    }, "description": {
        "en": "Order is overdue",
        "ko": "주문이 지연되었습니다."
    }, "color_code": "#683DE2"},
    {"code": "returned_order", "name": {
        "en": "Returned",
        "ko": "반환 주문"
    }, "description": {
        "en": "Order has been returned",
        "ko": "주문이 반환되었습니다."
    }, "color_code": "#1D9BE2"},
    {"code": "processed_order", "name": {
        "en": "Processed",
        "ko": "처리된 주문"
    }, "description": {
        "en": "Order processed after return",
        "ko": "주문이 반환 후 처리되었습니다."
    }, "color_code": "#9C9D9D"},

    # cancelled group
    {"code": "cancelled", "name": {
        "en": "Cancelled",
        "ko": "취소된 주문"
    }, "description": {
        "en": "Order has been cancelled",
        "ko": "주문이 취소되었습니다."
    }, "color_code": "#EE533D"},
    {"code": "receipt_cancelled", "name": {
        "en": "Receipt Cancelled",
        "ko": "접수 취소된 주문"
    }, "description": {
        "en": "Order has been cancelled",
        "ko": "주문이 취소되었습니다."
    }, "color_code": "#EE533D"},
]
for status in DELIVERY_STATUS_LIST:
    existing_obj = DeliveryStatus.objects.filter(code=status["code"]).first()
    if existing_obj:
        update_model_with_translations(existing_obj, status)
    else:
        create_model_with_translations(DeliveryStatus, status)