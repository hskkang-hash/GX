from django.core.management.base import BaseCommand
from django.db import transaction
from orders.models import OrderItemType
from core.multilanguage.request_handlers import update_model_with_translations, create_model_with_translations



class Command(BaseCommand):
    help = 'Creates 5 sample OrderItemType records'

    @transaction.atomic
    def handle(self, *args, **options):
        sample_types = [
            {
                "name": {
                    "en": "Agricultural products",
                    "ko": "농산물",
                    "th": "ผักผลไม้"
                },
                "code": "AGRI"
            },
            {
                "name": {
                    "en": "Marine products",
                    "ko": "수산물",
                    "th": "สินค้าทะเล"
                },
                "code": "MARI"
            },
            {
                "name": {
                    "en": "Electronics",
                    "ko": "전자제품",
                    "th": "อุปกรณ์ไฟฟ้า"
                },
                "code": "ELEC"
            },
            {
                "name": {
                    "en": "Books",
                    "ko": "서적",
                    "th": "หนังสือ"
                },
                "code": "BOOK"
            },
            {
                "name": {
                    "en": "Medicines",
                    "ko": "의약품",
                    "th": "ยา"
                },
                "code": "MEDI"
            },
            {
                "name": {
                    "en": "Cosmetics",
                    "ko": "화장품",
                    "th": "สบู่"
                },
                "code": "COSM"
            },
            {
                "name": {
                    "en": "Stationery",
                    "ko": "문구",
                    "th": "สมุด"
                },
                "code": "STY"
            },
            {
                "name": {
                    "en": "Documents",
                    "ko": "문서",
                    "th": "เอกสาร"
                },
                "code": "DOC"
            },
            {
                "name": {
                    "en": "Fragile Items",
                    "ko": "취급 주의",
                    "th": "ของที่ต้องระมัดระวัง"
                },
                "code": "FRAG"
            },
            {
                "name": {
                    "en": "Food",
                    "ko": "식품",
                    "th": "อาหาร"
                },
                "code": "FOOD"
            },
            {
                "name": {
                    "en": "Samples",
                    "ko": "시료",
                    "th": "ตัวอย่าง"
                },
                "code": "SAMP"
            },
            {
                "name": {
                    "en": "Newspaper",
                    "ko": "신문",
                    "th": "หนังสือพิมพ์"
                },
                "code": "NEW"
            },
            {
                "name": {
                    "en": "Seedlings",
                    "ko": "묘목",
                    "th": "ต้นไม้"
                },
                "code": "SEED"
            },
            {
                "name": {
                    "en": "Others",
                    "ko": "기타",
                    "th": "อื่นๆ"
                },
                "code": "OTHR"
            },
            {
                "name": {
                    "en": "Clothing",
                    "ko": "의류",
                    "th": "เสื้อผ้า"
                },
                "code": "CLOTH"
            }
        ]
        
        created_count = 0
        for item_type in sample_types:
            # Check if item type already exists
            existing_obj = OrderItemType.objects.filter(name__icontains=item_type["name"]["en"], code=item_type["code"]).first()
            if existing_obj:
                item_type["created_by"] = None
                item_type["modified_by"] = None
                update_model_with_translations(existing_obj, item_type)
                self.stdout.write(self.style.SUCCESS(f"Created OrderItemType: {item_type['name']} ({item_type['code']})"))
            else:
                item_type["created_by"] = None
                item_type["modified_by"] = None
                create_model_with_translations(OrderItemType, item_type)
                self.stdout.write(self.style.WARNING(f"OrderItemType with code {item_type['code']} already exists."))
        
        self.stdout.write(self.style.SUCCESS(f"Created {created_count} new OrderItemType records.")) 