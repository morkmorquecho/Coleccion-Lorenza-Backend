from django.apps import AppConfig


class PiecesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'pieces'
    verbose_name = 'Piezas'

    def ready(self):
        import pieces.signals
