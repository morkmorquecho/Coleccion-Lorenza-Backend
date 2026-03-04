# signals.py
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver

from core.utils.storages import borrar_archivo_storage
from .models import Piece, PiecePhoto


#=========================================== THUMBNAIL_PATH - PIECE ===========================================
# @receiver(post_delete, sender=Piece)
# def borrar_imagen_al_eliminar(sender, instance, **kwargs):
#     """Cuando se elimina el piece, borra su imagen de R2."""
#     borrar_archivo_storage(instance.thumbnail_path)


# @receiver(pre_save, sender=Piece)
# def borrar_imagen_anterior_al_actualizar(sender, instance, **kwargs):
#     """Cuando se actualiza la imagen o se desactiva el piece, borra la imagen de R2."""
#     if not instance.pk:
#         return  # Es un objeto nuevo, no hay imagen anterior

#     try:
#         piece_anterior = Piece.objects.get(pk=instance.pk)
#         imagen_anterior = piece_anterior.thumbnail_path
#     except Piece.DoesNotExist:
#         return

#     # Caso 1: se desactivó el piece (is_active cambió a False)
#     if piece_anterior.is_active and not instance.is_active:
#         borrar_archivo_storage(imagen_anterior)
#         # Borrar también las imágenes de los PiecePhoto asociados
#         for photo in instance.photos.all():
#             photo.delete()  # hard delete + borra archivo
#         return

#     # Caso 2: la imagen cambió
#     imagen_nueva = instance.thumbnail_path
#     imagen_nueva_name = imagen_nueva.name if imagen_nueva else None

#     if imagen_anterior and imagen_anterior.name and imagen_anterior.name != imagen_nueva_name:
#         borrar_archivo_storage(imagen_anterior)


# #=========================================== IMAGE_PATH - PHOTO PIECE ===========================================
# @receiver(post_delete, sender=PiecePhoto)
# def borrar_imagen_photo_al_eliminar(sender, instance, **kwargs):
#     """Cuando se elimina el PiecePhoto, borra su imagen de R2."""
#     borrar_archivo_storage(instance.image_path)


# @receiver(pre_save, sender=PiecePhoto)
# def borrar_imagen_photo_anterior_al_actualizar(sender, instance, **kwargs):
#     """Cuando se actualiza la imagen de un PiecePhoto, borra la anterior de R2."""
#     if not instance.pk:
#         return

#     try:
#         photo_anterior = PiecePhoto.objects.get(pk=instance.pk)
#         imagen_anterior = photo_anterior.image_path
#     except PiecePhoto.DoesNotExist:
#         return

#     imagen_nueva = instance.image_path
#     imagen_nueva_name = imagen_nueva.name if imagen_nueva else None

#     if imagen_anterior and imagen_anterior.name and imagen_anterior.name != imagen_nueva_name:
#         borrar_archivo_storage(imagen_anterior)


def _archivo_cambio(instance, anterior, field_name):
    """True si el archivo del campo cambió entre dos instancias."""
    archivo_anterior = getattr(anterior, field_name)
    archivo_nuevo = getattr(instance, field_name)
    nombre_nuevo = archivo_nuevo.name if archivo_nuevo else None
    return bool(archivo_anterior and archivo_anterior.name and archivo_anterior.name != nombre_nuevo)



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

    if _archivo_cambio(instance, anterior, 'thumbnail_path'):
        borrar_archivo_storage(anterior.thumbnail_path)

    if _archivo_cambio(instance, anterior, 'intro_video'):
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

    if _archivo_cambio(instance, anterior, 'image_path'):
        borrar_archivo_storage(anterior.image_path)