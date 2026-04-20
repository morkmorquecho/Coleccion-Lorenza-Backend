from typing import Collection

from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
from core.utils.storages import delete_file_fields, delete_if_changed
from .models import Carousel, ImageCollection


# ========================= CAROUSEL =============================
CAMPOS_CAROUSEL = ['img']

@receiver(post_delete, sender=Carousel)
def borrar_archivos_carousel_al_eliminar(sender, instance, **kwargs):
    delete_file_fields(instance, CAMPOS_CAROUSEL)


@receiver(pre_save, sender=Carousel)
def borrar_archivos_carousel_al_actualizar(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        anterior = Carousel.objects.get(pk=instance.pk)
    except Carousel.DoesNotExist:
        return

    delete_if_changed(anterior, instance, CAMPOS_CAROUSEL)


# ========================= COLLECTION =============================
CAMPOS_COLLECTION = ['thumbnail_path']

@receiver(post_delete, sender=Collection)
def borrar_archivos_collection_al_eliminar(sender, instance, **kwargs):
    delete_file_fields(instance, CAMPOS_COLLECTION)


@receiver(pre_save, sender=Collection)
def borrar_archivos_collection_al_actualizar(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        anterior = Collection.objects.get(pk=instance.pk)
    except Collection.DoesNotExist:
        return

    delete_if_changed(anterior, instance, CAMPOS_COLLECTION)


# ========================= IMAGE COLLECTION =============================
CAMPOS_IMAGE_COLLECTION = ['image_path']

@receiver(post_delete, sender=ImageCollection)
def borrar_archivos_image_collection_al_eliminar(sender, instance, **kwargs):
    delete_file_fields(instance, CAMPOS_IMAGE_COLLECTION)


@receiver(pre_save, sender=ImageCollection)
def borrar_archivos_image_collection_al_actualizar(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        anterior = ImageCollection.objects.get(pk=instance.pk)
    except ImageCollection.DoesNotExist:
        return

    delete_if_changed(anterior, instance, CAMPOS_IMAGE_COLLECTION)