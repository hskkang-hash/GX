from django.apps import AppConfig


class OperationalDataConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'operational_data'
    
    def ready(self):
        # Import tasks to ensure they're registered with Celery
        try:
            from . import tasks
        except ImportError:
            pass