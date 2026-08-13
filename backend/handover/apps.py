from django.apps import AppConfig


class HandoverConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'handover'
    verbose_name = 'Handover Management'
    
    def ready(self):
        """Import signals when app is ready"""
   

