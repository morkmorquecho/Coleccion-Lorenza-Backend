
import io
import pillow_heif
from PIL import Image
from django.core.files.base import ContentFile


class HEICConversionMixin:
    """
    Convierte automáticamente campos ImageField con HEIC/HEIF a JPEG antes de guardar.
    Uso: definir `heic_image_fields` con los nombres de los campos a procesar.
    """
    heic_image_fields: list[str] = []

    def save(self, *args, **kwargs):
        pillow_heif.register_heif_opener()

        for field_name in self.heic_image_fields:
            field = getattr(self, field_name, None)
            if field and hasattr(field, 'file'):
                converted = self._convert_heic_if_needed(field)
                if converted:
                    setattr(self, field_name, converted)

        super().save(*args, **kwargs)

    @staticmethod
    def _convert_heic_if_needed(image_field) -> ContentFile | None:
        try:
            img = Image.open(image_field)
        except Exception:
            return None

        if img.format not in ('HEIF', 'HEIC'):
            return None

        output = io.BytesIO()
        img.convert('RGB').save(output, format='JPEG', quality=90)
        output.seek(0)

        new_name = image_field.name.rsplit('.', 1)[0] + '.jpg'
        return ContentFile(output.read(), name=new_name)