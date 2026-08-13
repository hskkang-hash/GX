from django.core.management.base import BaseCommand
from flight_log.models import DroneAnomalyPrediction
from core.multilanguage.request_handlers import process_multilanguage_request, create_model_with_translations, update_model_with_translations


class Command(BaseCommand):
    help = 'Create sample DroneAnomalyPrediction instances (normal and warning)'

    def handle(self, *args, **options):
        # Create Normal prediction
        normal_prediction = {
            'name': {'en': 'Normal', 'ko': '정상'},
            'code': 'NORMAL',
            'description': 'Drone is operating normally with no anomalies detected'
        }
        existing_obj = DroneAnomalyPrediction.objects.filter(code=normal_prediction["code"]).first()
        if existing_obj:
            update_model_with_translations(existing_obj, normal_prediction)
            self.stdout.write(
                self.style.WARNING(f'Updated existing Normal DroneAnomalyPrediction: {normal_prediction["code"]}')
            )
        else:   
            create_model_with_translations(DroneAnomalyPrediction, normal_prediction)
            self.stdout.write(
                self.style.SUCCESS(f'Successfully created Normal DroneAnomalyPrediction: {normal_prediction["code"]}')
            )

        # Create Warning prediction
        warning_prediction = {
            'name': {'en': 'Warning', 'ko': '경고'},
            'code': 'WARNING',
            'description': 'Drone shows potential anomalies that require monitoring'
        }
        existing_obj = DroneAnomalyPrediction.objects.filter(code=warning_prediction["code"]).first()
        if existing_obj:
            update_model_with_translations(existing_obj, warning_prediction)
            self.stdout.write(
                self.style.WARNING(f'Updated existing Warning DroneAnomalyPrediction: {warning_prediction["code"]}')
            )
        else:
            create_model_with_translations(DroneAnomalyPrediction, warning_prediction)
            self.stdout.write(
                self.style.SUCCESS(f'Successfully created Warning DroneAnomalyPrediction: {warning_prediction["code"]}')
            )

        self.stdout.write(
            self.style.SUCCESS('Sample DroneAnomalyPrediction creation completed!')
        )
