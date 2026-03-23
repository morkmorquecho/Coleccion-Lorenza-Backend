# signals.py
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
from core.utils.storages import archivo_campo_cambio, borrar_archivo_storage
from .models import Piece, PiecePhoto, Review

#========================= PIECE =============================
@receiver(post_delete, sender=Piece)
def borrar_archivos_piece_al_eliminar(sender, instance, **kwargs):
    borrar_archivo_storage(instance.thumbnail_path)
    borrar_archivo_storage(instance.intro_video)


@receiver(pre_save, sender=Piece)
def borrar_archivos_piece_al_actualizar(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        anterior = Piece.objects.get(pk=instance.pk)
    except Piece.DoesNotExist:
        return

    if anterior.is_active and not instance.is_active:
        borrar_archivo_storage(anterior.thumbnail_path)
        borrar_archivo_storage(anterior.intro_video)
        for photo in instance.photos.all():
            photo.delete()
        return

    if archivo_campo_cambio(instance, anterior, 'thumbnail_path'):
        borrar_archivo_storage(anterior.thumbnail_path)

    if archivo_campo_cambio(instance, anterior, 'intro_video'):
        borrar_archivo_storage(anterior.intro_video)

#========================= IMAGE_PATH - PIECE PHOTO ========================================
@receiver(post_delete, sender=PiecePhoto)
def borrar_imagen_photo_al_eliminar(sender, instance, **kwargs):
    borrar_archivo_storage(instance.image_path)


@receiver(pre_save, sender=PiecePhoto)
def borrar_imagen_photo_anterior_al_actualizar(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        anterior = PiecePhoto.objects.get(pk=instance.pk)
    except PiecePhoto.DoesNotExist:
        return

    if archivo_campo_cambio(instance, anterior, 'image_path'):
        borrar_archivo_storage(anterior.image_path)

#========================= PHOTO - REVIEW ========================================

@receiver(post_delete, sender=Review)
def borrar_review_photo_al_eliminar(sender, instance, **kwargs):
    borrar_archivo_storage(instance.photo)


@receiver(pre_save, sender=Review)
def borrar_review_photo_anterior_al_actualizar(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        anterior = Review.objects.get(pk=instance.pk)
    except Review.DoesNotExist:
        return

    if archivo_campo_cambio(instance, anterior, 'photo'):
        borrar_archivo_storage(anterior.photo)
