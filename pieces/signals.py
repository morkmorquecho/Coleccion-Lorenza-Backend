# signals.py
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
from core.utils.storages import delete_file_fields, delete_if_changed
from .models import Piece, PiecePhoto, Review

#========================= PIECE =============================
CAMPOS_PIECE = ['thumbnail_path', 'intro_video']

@receiver(post_delete, sender=Piece)
def borrar_archivos_piece_al_eliminar(sender, instance, **kwargs):
    delete_file_fields(instance, CAMPOS_PIECE)


@receiver(pre_save, sender=Piece)
def borrar_archivos_piece_al_actualizar(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        anterior = Piece.objects.get(pk=instance.pk)
    except Piece.DoesNotExist:
        return

    # Si se desactiva la pieza, borrar todos sus archivos y fotos
    if anterior.is_active and not instance.is_active:
        delete_file_fields(anterior, CAMPOS_PIECE)
        for photo in instance.photos.all():
            photo.delete()
        return

    # Borrar archivos solo si cambiaron
    delete_if_changed(anterior, instance, CAMPOS_PIECE)


#========================= IMAGE_PATH - PIECE PHOTO ========================================
CAMPOS_PIECE_PHOTO = ['image_path']

@receiver(post_delete, sender=PiecePhoto)
def borrar_imagen_photo_al_eliminar(sender, instance, **kwargs):
    delete_file_fields(instance, CAMPOS_PIECE_PHOTO)


@receiver(pre_save, sender=PiecePhoto)
def borrar_imagen_photo_anterior_al_actualizar(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        anterior = PiecePhoto.objects.get(pk=instance.pk)
    except PiecePhoto.DoesNotExist:
        return

    delete_if_changed(anterior, instance, CAMPOS_PIECE_PHOTO)


#========================= PHOTO - REVIEW ========================================
CAMPOS_REVIEW = ['photo']

@receiver(post_delete, sender=Review)
def borrar_review_photo_al_eliminar(sender, instance, **kwargs):
    delete_file_fields(instance, CAMPOS_REVIEW)


@receiver(pre_save, sender=Review)
def borrar_review_photo_anterior_al_actualizar(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        anterior = Review.objects.get(pk=instance.pk)
    except Review.DoesNotExist:
        return

    delete_if_changed(anterior, instance, CAMPOS_REVIEW)