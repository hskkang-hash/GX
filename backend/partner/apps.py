from django.apps import AppConfig


class PartnerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'partner'
    
    def ready(self):
        """Import partner signals when app is ready"""
        try:
            import partner.signals  # noqa
        except ImportError:
            pass