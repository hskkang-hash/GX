from django.apps import AppConfig


class DeliveryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "delivery"

    def ready(self):
        from delivery.signals import (
            track_delivery_operation_status_change,
            store_old_delivery_status,
            create_report_on_delivered,
        )

        # Update delivery statuses
        try:
            from backend.delivery.models import DeliveryStatus
            from backend.delivery.constants import DELIVERY_STATUS_LIST

            for status in DELIVERY_STATUS_LIST:
                DeliveryStatus.objects.update_or_create(
                    code=status["code"],
                    defaults={
                        "name": status["name"],
                        "description": status.get("description", ""),
                        "color_code": status.get("color_code", ""),
                    },
                )
        except Exception as e:
            pass

        # Update cancellation reasons
        try:
            from backend.delivery.models import DeliveryCancellationReason
            from backend.delivery.constants import CANCELLATION_TYPE_LIST

            for cancellation_type in CANCELLATION_TYPE_LIST:
                DeliveryCancellationReason.objects.update_or_create(
                    code=cancellation_type["code"],
                    defaults={
                        "reason_default": cancellation_type.get("reason_default", ""),
                    },
                )
        except Exception as e:
            pass
