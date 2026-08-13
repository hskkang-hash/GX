from django.apps import AppConfig


class TerminalsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'terminals'
    
    def ready(self):
        """Đăng ký signals khi app được load"""
        import terminals.signals  # noqa 