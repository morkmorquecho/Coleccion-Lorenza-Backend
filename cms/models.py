from datetime import date

from django.db import models
from jsonschema import ValidationError

from cms.utils import upload_image_carousel, upload_image_collection, validate_jpg, validate_year
from core.mixins import ImagenPKMixin
from core.models import BaseModel


class Carousel(ImagenPKMixin, BaseModel):
    CAROUSEL_CHOICES = [
        (1, 'Primero'),
        (2, 'Segundo'),
        (3, 'Tercero'),
    ]

    POSITION_CHOICES = [
        (1, 'Primero'),
        (2, 'Segundo'),
        (3, 'Tercero'),
        (4, 'Cuarto'),
        (5, 'Quinto'),
    ]
    
    carousel = models.IntegerField(choices=CAROUSEL_CHOICES)
    position = models.IntegerField(choices=POSITION_CHOICES)
    from django.core.exceptions import ValidationError

    img = models.ImageField(upload_to=upload_image_carousel, validators=[validate_jpg])

    def __str__(self):
        return f"carousel:{self.carousel} - position:{self.position}"

    class Meta:
        unique_together = (('carousel', 'position'),)
        verbose_name = 'Carrusel'
        verbose_name_plural = 'Carruseles'


class Collection(ImagenPKMixin, BaseModel):
    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True, null=True)
    thumbnail_path = models.ImageField(upload_to=upload_image_collection)
    featured = models.BooleanField(default=False)
    
    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.featured:
            qs = Collection.objects.filter(featured=True)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.count() >= 3:
                from django.core.exceptions import ValidationError
                raise ValidationError("Solo puede haber 3 colecciones destacadas.")
        super().save(*args, **kwargs)

    class Meta:        
        verbose_name = 'Coleccion'
        verbose_name_plural = 'Colecciones'


class ImageCollection(ImagenPKMixin, BaseModel):
    collection = models.ForeignKey(
        Collection,
        on_delete=models.CASCADE,
        related_name='images'
    )
    image_path = models.ImageField(upload_to=upload_image_collection)
    year = models.PositiveSmallIntegerField(validators=[validate_year])
    name = models.CharField(max_length=150)

    def __str__(self):
        return f"{self.name} ({self.year}) - {self.collection.name}"
    
    class Meta:        
        verbose_name = 'Imagen de coleccion'
        verbose_name_plural = 'Imagenes de colecciones'
