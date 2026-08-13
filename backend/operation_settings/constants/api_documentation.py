# API Documentation Constants
# This file contains the documentation for supported APIs

DELIVERY_APIS = [
    {
        "name": "order_inquiry",
        "method": "POST", 
        "url": "/api/delivery/order-inquiry",
        "description": "Create new order inquiry - Initialize order with validation",
        "auth_required": True,
        "parameters": {
            "query_params": {},
            "path_params": {},
            "headers": {
                "Authorization": "Bearer <jwt_token>",
                "Content-Type": "application/json"
            },
            "body_schema": {
                "required_fields": {
                    "recipient_name": "string - Name of recipient",
                    "recipient_phone": "string - Phone number of recipient", 
                    "pickup_location_id": "integer - ID of pickup terminal"
                },
                "optional_fields": {
                    "sender_name": "string - Name of sender",
                    "sender_phone": "string - Phone number of sender",
                    "recipient_address": {
                        "street": "string",
                        "city": "string", 
                        "district": "string",
                        "ward": "string",
                        "postal_code": "string (optional)",
                        "latitude": "float (optional)",
                        "longitude": "float (optional)"
                    },
                    "delivery_option_code": "string - Default: terminal_to_terminal",
                    "payment_method_code": "string - Default: cash",
                    "delivery_terminal_id": "integer - ID of delivery terminal",
                    "sender_note": "string - Sender notes",
                    "recipient_note": "string - Recipient notes", 
                    "currency": "string - Default: KRW",
                    "items": [
                        {
                            "package_id": "integer - Package specification ID",
                            "weight": {"value": "float", "unit": "string"},
                            "dimension_l": {"value": "float", "unit": "string"},
                            "dimension_w": {"value": "float", "unit": "string"},
                            "dimension_h": {"value": "float", "unit": "string"},
                            "is_waterproof": "boolean - Default: false",
                            "is_fragile": "boolean - Default: false",
                            "item_type_id": "integer (optional)",
                            "note": "string (optional)"
                        }
                    ]
                }
            }
        },
        "response_example": {
            "status_code": 201,
            "message": "Order inquiry created successfully",
            "data": {
                "order_id": 123,
                "order_code": "00000001",
                "status": "awaiting_payment",
                "total_amount": 20000.0,
                "currency": "KRW",
                "payment_status": "pending",
                "items_count": 2,
                "items": [
                    {
                        "item_id": 1,
                        "code": "PK000001",
                        "package_id": 1,
                        "amount": 10000
                    }
                ],
                "pickup_location": {
                    "id": 1,
                    "name": "Terminal A"
                },
                "delivery_terminal": {
                    "id": 2,
                    "name": "Terminal B"
                },
                "recipient": {
                    "name": "John Doe",
                    "phone": "010-1234-5678"
                },
                "sender": {
                    "name": "Jane Smith",
                    "phone": "010-8765-4321"
                }
            }
        },
        "error_responses": {
            "400": "Bad Request - Missing required fields or validation error",
            "404": "Not Found - Referenced data not found (terminal, package, etc.)",
            "500": "Internal Server Error"
        }
    },
    {
        "name": "change_order_status",
        "method": "POST",
        "url": "/api/delivery/change-order-status", 
        "description": "Change order status based on operation settings workflow",
        "auth_required": True,
        "parameters": {
            "query_params": {},
            "path_params": {},
            "headers": {
                "Authorization": "Bearer <jwt_token>",
                "Content-Type": "application/json"
            },
            "body_schema": {
                "required_fields": {
                    "order_id": "integer - ID of the order to change status"
                }
            }
        },
        "response_example": {
            "status_code": 200,
            "message": "Order status changed successfully",
            "data": {
                "order_id": 123,
                "delivery_operation_id": 456,
                "old_status": "unverified_order",
                "new_status": "verified_order"
            }
        },
        "error_responses": {
            "400": "Bad Request - No next status available or workflow error",
            "404": "Not Found - Order not found or delivery menu not configured",
            "500": "Internal Server Error"
        }
    }
]


