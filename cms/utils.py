from datetime import date
import os
import uuid
from django.core.exceptions import ValidationError


def validate_year(value):
    current_year = date.today().year
    if value <= 2020 or value > current_year:
        raise ValidationError(
            f"El año debe ser mayor a 2020 y menor o igual a {current_year}."
        )

ALLOWED_IMAGE_FORMATS = ('.jpg', '.jpeg', '.png', '.webp', '.heic', '.heif')

def validate_image_format(image):
    if not image.name.lower().endswith(ALLOWED_IMAGE_FORMATS):
        raise ValidationError(f'Formatos permitidos: {", ".join(ALLOWED_IMAGE_FORMATS)}')

def upload_image_carousel(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    identificador = instance.position if instance.position else uuid.uuid4().hex
    return f"carrusel/{instance.carousel}/img-{identificador}{ext}"

def upload_image_collection(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    collection_id = instance.collection_id  
    identificador = collection_id if collection_id else uuid.uuid4().hex
    return f"collection/{identificador}/{instance.pk or uuid.uuid4().hex}{ext}"

def upload_image_collection(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    identificador = instance.pk if instance.pk else uuid.uuid4().hex
    return f"collection/thumbnail/{identificador}{ext}"