from django.core.management.base import BaseCommand
from django.db import transaction
from terminals.models import LocationType, Terminal, TerminalType
from core.multilanguage.request_handlers import create_model_with_translations, update_model_with_translations

class Command(BaseCommand):
    help = 'Creates sample terminals with realistic data'

    @transaction.atomic
    def handle(self, *args, **options):
        # First, ensure we have terminal types
        terminal_types = self._create_terminal_types()
        
        # Sample terminals with realistic GPS coordinates for Vietnam
        sample_terminals = [
            {
                "name": "Noi Bai Terminal",
                "terminal_type": terminal_types[0],
                "latitude": 21.218536,
                "longitude": 105.804317,
                "city_province": "Hanoi",
                "city_county_district": "Soc Son District",
                "ward_town_township": "Phu Minh",
                "street_address": "Noi Bai International Airport",
                "note": "Main airport terminal in Hanoi",
                "status": "active"
            },
            {
                "name": "Saigon Central Hub",
                "terminal_type": terminal_types[1],
                "latitude": 10.823099,
                "longitude": 106.629664,
                "city_province": "Ho Chi Minh City",
                "city_county_district": "District 1",
                "ward_town_township": "Ben Nghe",
                "street_address": "123 Nguyen Hue Boulevard",
                "note": "Central delivery hub in HCMC",
                "status": "active"
            },
            {
                "name": "Da Nang Logistics Center",
                "terminal_type": terminal_types[1],
                "latitude": 16.031967,
                "longitude": 108.222882,
                "city_province": "Da Nang",
                "city_county_district": "Hai Chau District",
                "ward_town_township": "Hai Chau 1",
                "street_address": "456 Tran Phu Street",
                "note": "Main logistics terminal in Da Nang",
                "status": "active"
            },
            {
                "name": "Hue Distribution Center",
                "terminal_type": terminal_types[2],
                "latitude": 16.463713,
                "longitude": 107.590866,
                "city_province": "Thua Thien Hue",
                "city_county_district": "Hue City",
                "ward_town_township": "Phu Hoi",
                "street_address": "789 Le Loi Street",
                "note": "Main distribution center in Hue",
                "status": "active"
            },
            # {
            #     "name": "Can Tho Pickup Point",
            #     "terminal_type": terminal_types[3],
            #     "latitude": 10.034473,
            #     "longitude": 105.774857,
            #     "city_province": "Can Tho",
            #     "city_county_district": "Ninh Kieu District",
            #     "ward_town_township": "Tan An",
            #     "street_address": "321 Nguyen Trai Street",
            #     "note": "Pickup point for Mekong Delta region",
            #     "status": "active"
            # }
        ]
        
        created_count = 0
        for terminal_data in sample_terminals:
            terminal_type = terminal_data.pop("terminal_type")
            
            # Check if terminal already exists
            if not Terminal.objects.filter(name=terminal_data["name"]).exists():
                print("terminal_type", terminal_type.get("code"))
                terminal = Terminal.objects.create(
                    terminal_type=TerminalType.objects.get(code=terminal_type.get("code")),
                    **terminal_data
                )
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"Created Terminal: {terminal.name}"))
            else:
                self.stdout.write(self.style.WARNING(f"Terminal {terminal_data['name']} already exists."))
        
        self.stdout.write(self.style.SUCCESS(f"Created {created_count} new Terminal records."))
    
    def _create_terminal_types(self):
        # Sample terminal types
        terminal_types_data = [
            # {"name": {
            #     "en": "Airport Terminal",
            #     "ko": "공항 터미널"
            # }, "code": "AIRPORT", "description": {
            #     "en": "For airports and related logistics facilities",
            #     "ko": "공항 및 관련 물류 시설"
            # }},
            {"name": {
                "en": "Warehouse",
                "ko": "창고"
            }, "code": "WAREHOUSE", "description": {
                "en": "Storage warehouses and distribution centers",
                "ko": "창고 및 배송 센터"
            }},
            {"name": {
                "en": "Distribution Center",
                "ko": "물류 센터"
            }, "code": "DISTRIBUTION", "description": {
                "en": "Main distribution hubs",
                "ko": "주요 배송 센터"
            }},
            {"name": {
                "en": "Pickup Point",
                "ko": "픽업 지점"
            }, "code": "PICKUP", "description": {
                "en": "Customer pickup locations",
                "ko": "고객 픽업 지점"
            }}
        ]
        
        for type_data in terminal_types_data:
            code = type_data["code"]
            terminal_type, created = TerminalType.objects.get_or_create(
                code=code,
                defaults=type_data
            )
            if created:
                create_model_with_translations(TerminalType, type_data)
                self.stdout.write(self.style.SUCCESS(f"Created Terminal Type: {terminal_type.name}"))
            else:
                update_model_with_translations(terminal_type, type_data)
                self.stdout.write(self.style.WARNING(f"Terminal Type {terminal_type.name} already exists."))
        
        return terminal_types_data 