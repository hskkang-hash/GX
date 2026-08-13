from django.core.management.base import BaseCommand
from core.configuration.models import AdminConfig
from django.db import transaction
from terminals.models import RouteService
from core.multilanguage.request_handlers import create_model_with_translations, update_model_with_translations
class Command(BaseCommand):
    help = 'Initialize route service data'

    def handle(self, *args, **options):
        self.stdout.write('Starting to initialize route service data...')
        route_services = [
            {
                'name': {
                    'en': 'Delivery',
                    'ko': '배송',
                    'th': 'การจัดส่ง'
                },
                'code': 'DELIVERY'
            },
            {
                'name': {
                    'en': 'Surveillance',
                    'ko': '감시',
                    'th': 'การสอบสวน'
                },
                'code': 'SURVEILLANCE'
            }
        ]
        try:
            with transaction.atomic():
                # Check if existing
                for route_service in route_services:
                    existing_route_service = RouteService.objects.filter(code=route_service['code']).first()
                    if not existing_route_service:
                        create_model_with_translations(RouteService, route_service)
                        self.stdout.write(self.style.SUCCESS(f'Route service data created successfully: {route_service["name"]["en"]}'))
                    else:
                        update_model_with_translations(existing_route_service, route_service)
                        self.stdout.write(self.style.SUCCESS(f'Route service data updated successfully: {route_service["name"]["en"]}'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error initializing route service data: {e}'))