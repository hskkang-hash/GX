from orders.models import Order, OrderHistory, OrderStatus
from core.multilanguage.request_handlers import create_model_with_translations

class OrderRepository:
    @staticmethod
    def get_order_by_id(order_id: int) -> Order:
        return Order.objects.get(id=order_id)
    
    @staticmethod
    def update_order_status(order_id: int, status_code: str) -> None:
        order = Order.objects.get(id=order_id)
        status = OrderStatus.objects.get(code=status_code)
        order.status = status
        order.save()

    @staticmethod
    def update_orders_status(order_ids: list, status_code: str) -> None:
        orders = Order.objects.filter(id__in=order_ids)
        status = OrderStatus.objects.get(code=status_code)
        for order in orders:
            order.status = status
            order.save()

    @staticmethod
    def create_order_create_history(order_id: int, username: str) -> None:
        order = Order.objects.get(id=order_id)
        order_history = {
            "order": order,
            "action": "created",
            "description": {
                "en": f"Order created by {username}" if username != "" else "Order created",
                "ko": f"{username}님이 주문을 생성하였습니다." if username != "" else "주문을 생성하였습니다.",
                "th": f"{username} สร้างคำสั่งซื้อ" if username != "" else "คำสั่งซื้อสร้าง"
            }
        }
        create_model_with_translations(OrderHistory, order_history)

    @staticmethod
    def create_order_paid_history(order_id: int, username: str) -> None:
        order = Order.objects.get(id=order_id)
        order_history = {
            "order": order,
            "action": "paid",
            "description": {
                "en": f"Order paid by {username}" if username != "" else "Order paid",
                "ko": f"{username}님이 주문을 결제하였습니다." if username != "" else "주문을 결제하였습니다.",
                "th": f"{username} ชำระเงิน" if username != "" else "ชำระเงิน"
            }
        }
        create_model_with_translations(OrderHistory, order_history)

    @staticmethod
    def create_order_cancelled_history(order_id: int, username: str) -> None:
        order = Order.objects.get(id=order_id)
        order_history = {
            "order": order,
            "action": "cancelled",
            "description": {
                "en": f"Order cancelled by {username}" if username != "" else "Order cancelled",
                "ko": f"{username}님이 주문을 취소하였습니다." if username != "" else "주문을 취소하였습니다.",
                "th": f"{username} ยกเลิกคำสั่งซื้อ" if username != "" else "ยกเลิกคำสั่งซื้อ"
            }
        }
        create_model_with_translations(OrderHistory, order_history)

    @staticmethod
    def create_order_refunded_history(order_id: int, username: str) -> None:
        order = Order.objects.get(id=order_id)
        order_history = {
            "order": order,
            "action": "refunded",
            "description": {
                "en": f"Order refunded by {username}" if username != "" else "Order refunded",
                "ko": f"{username}님이 주문을 환불하였습니다." if username != "" else "주문을 환불하였습니다.",
                "th": f"{username} คืนเงิน" if username != "" else "คืนเงิน"
            }
        }
        create_model_with_translations(OrderHistory, order_history)

    @staticmethod
    def create_order_verified_history(order_id: int, username: str) -> None:
        order = Order.objects.get(id=order_id)
        order_history = {
            "order": order,
            "action": "verified",
            "description": {
                "en": f"Order verified by {username}" if username != "" else "Order verified",
                "ko": f"{username}님이 주문을 확인하였습니다." if username != "" else "주문을 확인하였습니다.",
                "th": f"{username} ตรวจสอบคำสั่งซื้อ" if username != "" else "ตรวจสอบคำสั่งซื้อ"
            }
        }
        create_model_with_translations(OrderHistory, order_history)

    @staticmethod
    def create_orders_verified_history(order_ids: list, username: str) -> None:
        orders = Order.objects.filter(id__in=order_ids)
        for order in orders:
            order_history = {
                "order": order,
                "action": "verified",
                "description": {
                    "en": f"Order verified by {username}" if username != "" else "Order verified",
                    "ko": f"{username}님이 주문을 확인하였습니다." if username != "" else "주문을 확인하였습니다.",
                    "th": f"{username} ตรวจสอบคำสั่งซื้อ" if username != "" else "ตรวจสอบคำสั่งซื้อ"
                }
            }
            create_model_with_translations(OrderHistory, order_history)

    @staticmethod
    def create_order_returned_history(order_id: int, username: str) -> None:
        order = Order.objects.get(id=order_id)
        order_history = {
            "order": order,
            "action": "returned",
            "description": {
                "en": f"Order returned by {username}" if username != "" else "Order returned",
                "ko": f"{username}님이 주문을 반품하였습니다." if username != "" else "주문을 반품하였습니다.",
                "th": f"{username} คืนคำสั่งซื้อ" if username != "" else "คืนคำสั่งซื้อ"
            }           
        }
        create_model_with_translations(OrderHistory, order_history)

    @staticmethod
    def create_order_delivered_history(order_id: int, username: str) -> None:
        order = Order._base_manager.get(id=order_id)
        order_history = {
            "order": order,
            "action": "completed",
            "description": {
                "en": f"Order completed",
                "ko": f"주문이 완료되었습니다.",    
                "th": f"คำสั่งซื้อสำเร็จ"
            }
        }
        create_model_with_translations(OrderHistory, order_history)

    @staticmethod
    def create_order_receipt_cancelled_history(order_id: int, username: str) -> None:
        order = Order.objects.get(id=order_id)
        order_history = {
            "order": order,
            "action": "receipt_cancelled",
            "description": {
                "en": f"Order receipt cancelled by {order.recipient_name}" if order.recipient_name != "" else "Order receipt cancelled",
                "ko": f"{order.recipient_name}님이 주문을 접수 취소하였습니다." if order.recipient_name != "" else "주문을 접수 취소하였습니다.",
                "th": f"{order.recipient_name} ยกเลิกคำสั่งซื้อ" if order.recipient_name != "" else "ยกเลิกคำสั่งซื้อ"
            }
        }
        create_model_with_translations(OrderHistory, order_history)