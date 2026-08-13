from django.apps import AppConfig


class OperationSettingsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'operation_settings'
    verbose_name = 'Operation Settings'
    
    # def ready(self):
    #     """Register signals when the app is ready""" 