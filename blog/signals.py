from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
from core.utils.storages import borrar_archivo_storage, archivo_campo_cambio
from .models import Blog

# ========================= BLOG =============================
@receiver(post_delete, sender=Blog)
def borrar_archivos_blog_al_eliminar(sender, instance, **kwargs):
    borrar_archivo_storage(instance.cover_image)


@receiver(pre_save, sender=Blog)
def borrar_archivos_blog_al_actualizar(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        anterior = Blog.objects.get(pk=instance.pk)
    except Blog.DoesNotExist:
        return

    if archivo_campo_cambio(instance, anterior, 'cover_image'):
        borrar_archivo_storage(anterior.cover_image)
