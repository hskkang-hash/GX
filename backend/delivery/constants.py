DELIVERY_STATUS_LIST = [
    # verification group
    {"code": "unverified_order", "name": "Unverified Order", "description": "Order not yet verified", "color_code": "#FFA500"},
    {"code": "verified_order", "name": "Verified Order", "description": "Order has been verified", "color_code": "#00BFFF"},

    # processing group
    {"code": "select_route_processing", "name": "Select Route", "description": "Select delivery route", "color_code": "#1E90FF"},
    {"code": "select_drone_processing", "name": "Select Drone", "description": "Select delivery drone", "color_code": "#4682B4"},
    {"code": "in_transit_processing", "name": "In Transit Processing", "description": "Drone is delivering the order", "color_code": "#6495ED"},

    # completed group
    {"code": "arrived_order", "name": "Arrived Order", "description": "Arrived at warehouse", "color_code": "#32CD32"},
    {"code": "completed_order", "name": "Completed Order", "description": "Successfully delivered", "color_code": "#228B22"},

    # return group
    {"code": "order_due_for_returned", "name": "Order Due For Return", "description": "Order needs to be returned", "color_code": "#FFD700"},
    {"code": "order_pending_returned", "name": "Order Pending Return", "description": "Order pending return", "color_code": "#FF8C00"},
    {"code": "overdue_order", "name": "Overdue Order", "description": "Order is overdue", "color_code": "#DC143C"},
    {"code": "returned_order", "name": "Returned Order", "description": "Order has been returned", "color_code": "#8B0000"},
    {"code": "processed_order", "name": "Processed Order", "description": "Order processed after return", "color_code": "#A0522D"},

    # cancelled group
    {"code": "cancelled", "name": "Cancelled", "description": "Order has been cancelled", "color_code": "#808080"},
    {"code": "receipt_cancelled", "name": "Receipt Cancelled", "description": "Order has been receipt cancelled", "color_code": "#808080"},
]

CANCELLATION_TYPE_LIST = [
    {
        "code": "auto_cancelled",
        "reason_default": "Order was automatically cancelled due to payment timeout",
    },
    {
        "code": "user_cancelled",
        "reason_default": "Order was cancelled by user",
    },
]

# Order timeout no pickup default (day)
ARRIVED_ORDER_TIMEOUT_NO_PICKUP_DEFAULT = 30
PENDING_ORDER_TIMEOUT_NO_PICKUP_DEFAULT = 15