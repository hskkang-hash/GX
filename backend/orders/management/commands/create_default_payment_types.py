from django.core.management.base import BaseCommand
from django.db import transaction
from orders.models import PaymentType
from core.multilanguage.request_handlers import process_multilanguage_request, create_model_with_translations, update_model_with_translations, get_model_with_translations


class Command(BaseCommand):
    help = 'Creates default PaymentType records'

    @transaction.atomic
    def handle(self, *args, **options):
        payment_types = [
            {
                "name": {
                    "en": "Cash",
                    "ko": "현금",
                    "th": "เงินสด"
                },
                "code": "cash",
                "provider": "Physical",
                "method": "Cash Payment",
                "is_active": True,
                "note": "Traditional cash payment upon delivery or pickup."
            },
            {
                "name": {
                    "en": "KaKao Pay",
                    "ko": "카카오페이",
                    "th": "กูโกเปย์"
                },
                "code": "kakao_pay",
                "provider": "KaKao",
                "method": "Mobile Payment",
                "is_active": True,
                "note": "Mobile payment through KaKao Pay platform."
            },
            {
                "name": {
                    "en": "Credit Card / Debit Card",
                    "ko": "신용카드 / 직불카드",
                    "th": "บัตรเครดิต / บัตรเดบิต"
                },
                "code": "card",
                "provider": "Bank",
                "method": "Card Payment",
                "is_active": True,
                "note": "Card payment at delivery or online."
            },
            {
                "name": {
                    "en": "Bank Transfer / Wire Transfer",
                    "ko": "은행 이체 / 외화 이체",
                    "th": "การโอนเงินผ่านธนาคาร / การโอนเงินผ่านสายไฟ"
                },
                "code": "bank_transfer",
                "provider": "Bank",
                "method": "Transfer",
                "is_active": True,
                "note": "Payment through bank transfer or wire transfer."
            }
        ]
        
        created_count = 0
        for payment_type_data in payment_types:
            # Check if payment type already exists by code
            existing_obj = PaymentType.objects.filter(code=payment_type_data["code"]).first()
            if existing_obj:
                update_model_with_translations(existing_obj, payment_type_data)
            else:
                create_model_with_translations(PaymentType, payment_type_data)
            
            created_count += 1
            self.stdout.write(self.style.SUCCESS(f"Created PaymentType: {payment_type_data['name']}"))
        
        self.stdout.write(self.style.SUCCESS(f"Created {created_count} new PaymentType records.")) 