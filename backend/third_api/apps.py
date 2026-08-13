from django.apps import AppConfig


class ThirdApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'third_api'
    verbose_name = 'Third Party API Integration'
    
    def ready(self):
        """Import signals when app is ready"""
        import third_api.signals 