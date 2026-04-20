from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
from core.utils.storages import delete_file_fields, delete_if_changed
from .models import Blog

# ========================= BLOG =============================
CAMPOS_BLOG = ['cover_image']

@receiver(post_delete, sender=Blog)
def borrar_archivos_blog_al_eliminar(sender, instance, **kwargs):
    delete_file_fields(instance, CAMPOS_BLOG)


@receiver(pre_save, sender=Blog)
def borrar_archivos_blog_al_actualizar(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        anterior = Blog.objects.get(pk=instance.pk)
    except Blog.DoesNotExist:
        return

    delete_if_changed(anterior, instance, CAMPOS_BLOG)