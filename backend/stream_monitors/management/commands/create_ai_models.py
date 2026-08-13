from django.core.management.base import BaseCommand
from stream_monitors.models import AIModel
from core.multilanguage.request_handlers import create_model_with_translations, update_model_with_translations


class Command(BaseCommand):
    help = 'Create AI Model records for detecting anomaly, vehicle, human, animals, and fire smoke'

    def handle(self, *args, **options):
        ai_models_data = [
            
            {
                'name': {'en': 'Vehicle', 'ko': '차량', 'th': 'ยานพาหนะ'},
                'description': {'ko': '비디오 스트림에서 차량을 감지하는 AI 모델', 'en': 'AI model for detecting vehicles in video streams'}, 
                'code': 'vehicle',
                'link': 'https://example.com/models/vehicle-detection',
                'is_active': True
            },
            
            {
                'name': {'en': 'Human', 'ko': '인간', 'th': 'มนุษย์'},
                'description': {'en': 'AI model for detecting humans in video streams', 'ko': '비디오 스트림에서 인간을 감지하는 AI 모델'},
                'code': 'human',
                'link': 'https://example.com/models/human-detection',
                'is_active': True
            },
            
            {
                'name': {'en': 'Animals', 'ko': '동물', 'th': 'สัตว์'},
                'description': {'en': 'AI model for detecting animals in video streams', 'ko': '비디오 스트림에서 동물을 감지하는 AI 모델'},
                'code': 'animals',
                'link': 'https://example.com/models/animal-detection',
                'is_active': True
            },
            
            {
                'name': {'en': 'Fire Smoke', 'ko': '화재 및 연기', 'th': 'ความร้อนและความเข้ม'},
                'description': {'en': 'AI model for detecting fire and smoke in video streams', 'ko': '비디오 스트림에서 화재와 연기를 감지하는 AI 모델'},
                'code': 'fire_smoke',
                'link': 'https://example.com/models/fire-smoke-detection',
                'is_active': True
            }
        ]

        created_count = 0
        for model_data in ai_models_data:
            existing_obj = AIModel.objects.filter(code=model_data["code"]).first()
            if existing_obj:
                update_model_with_translations(existing_obj, model_data)
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"Updated AI Model: {model_data['name']}"))
            else:
                create_model_with_translations(AIModel, model_data)
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"Created AI Model: {model_data['name']}"))

        self.stdout.write(
            self.style.SUCCESS(f'Command completed. {created_count} new AI Models created.')
        ) 