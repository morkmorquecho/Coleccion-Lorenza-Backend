from typing import Collection

from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
from core.utils.storages import borrar_archivo_storage, archivo_campo_cambio
from .models import Carousel, ImageCollection


# ========================= CAROUSEL =============================
@receiver(post_delete, sender=Carousel)
def borrar_archivos_carousel_al_eliminar(sender, instance, **kwargs):
    borrar_archivo_storage(instance.img)


@receiver(pre_save, sender=Carousel)
def borrar_archivos_carousel_al_actualizar(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        anterior = Carousel.objects.get(pk=instance.pk)
    except Carousel.DoesNotExist:
        return

    if archivo_campo_cambio(instance, anterior, 'img'):
        borrar_archivo_storage(anterior.img)

# ========================= COLLECTION =============================
@receiver(post_delete, sender=Collection)
def borrar_archivos_collection_al_eliminar(sender, instance, **kwargs):
    borrar_archivo_storage(instance.thumbnail_path)

@receiver(pre_save, sender=Collection)
def borrar_archivos_collection_al_actualizar(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        anterior = Collection.objects.get(pk=instance.pk)
    except Collection.DoesNotExist:
        return

    if archivo_campo_cambio(instance, anterior, 'thumbnail_path'):
        borrar_archivo_storage(anterior.thumbnail_path)


# ========================= IMAGE COLLECTION =============================
@receiver(post_delete, sender=ImageCollection)
def borrar_archivos_image_collection_al_eliminar(sender, instance, **kwargs):
    borrar_archivo_storage(instance.image_path)


@receiver(pre_save, sender=ImageCollection)
def borrar_archivos_image_collection_al_actualizar(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        anterior = ImageCollection.objects.get(pk=instance.pk)
    except ImageCollection.DoesNotExist:
        return

    if archivo_campo_cambio(instance, anterior, 'image_path'):
        borrar_archivo_storage(anterior.image_path)