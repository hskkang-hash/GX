from django.apps import AppConfig


class StreamMonitorsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'stream_monitors'

    def ready(self):
        # Initialize any startup tasks here if needed
        pass