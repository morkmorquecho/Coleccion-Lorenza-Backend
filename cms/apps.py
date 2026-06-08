from django.apps import AppConfig


class CmsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'cms'
    verbose_name =  'Sistema de Gestión de Contenido'

    def ready(self):
        import cms.signals    
        import pillow_heif
        pillow_heif.register_heif_opener()
        
