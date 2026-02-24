from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.utils import timezone
from core.mixins import ImagenPKMixin
from core.models import BaseModel
from core.utils.storages import borrar_archivo_storage
from pieces.utils import upload_piece_image, upload_pieces_thumb
from django.core.validators import MinValueValidator, MaxValueValidator


class TypePiece(BaseModel):
    type = models.CharField(max_length=100, unique=True)
    key = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ['type']
        verbose_name = 'Tipo de pieza'
        verbose_name_plural = 'Tipos de pieza'

    def __str__(self):
        return f"{self.type} ({self.key})"

class Section(BaseModel):
    section = models.CharField(max_length=100, unique=True)
    key = models.CharField(max_length=100, unique=True)
    class Meta:
        verbose_name = 'Seccion'
        verbose_name_plural = 'Secciones'
        ordering = ['section']


    def __str__(self):
        return f"{self.section} ({self.key})"
    

class Piece(ImagenPKMixin, BaseModel):
    thumbnail_path = models.ImageField(upload_to=upload_pieces_thumb)
    title = models.CharField(max_length=100, unique=True)
    slug = models.CharField(blank=True, null=True, unique=True, max_length=100)
    description = models.TextField()
    
    quantity = models.IntegerField()
    price_mx = models.DecimalField(max_digits=10, decimal_places=2)
    price_usa = models.DecimalField(max_digits=10, decimal_places=2)

    width = models.DecimalField(max_digits=10, decimal_places=2)
    height = models.DecimalField(max_digits=10, decimal_places=2)
    length = models.DecimalField(max_digits=10, decimal_places=2)
    weight = models.DecimalField(max_digits=4, decimal_places=2)

    customizable = models.BooleanField(default=False)
    featured = models.BooleanField(default=False)

    type = models.ForeignKey(TypePiece, on_delete=models.CASCADE, related_name="pieces")
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="pieces")
    class Meta:
        verbose_name = 'Pieza'
        verbose_name_plural = 'Piezas'

    def __str__(self):
        return self.title

    
    @property
    def volumetric_weight(self):
        return max((self.width * self.height * self.length) / 5000, 1)

    def clean(self):
        if self.price_mx >= self.price_usa:
            raise ValidationError({
                'price_mx': 'price_mx debe ser menor que price_usa'
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        

class Discount(BaseModel):
    percentage = models.DecimalField( max_digits=3, decimal_places=1, validators=[MinValueValidator(0.1)])
    start_date = models.DateField()
    end_date = models.DateField()

    class Meta:
        verbose_name = 'Descuento'
        verbose_name_plural = 'Descuentos'
        ordering = ['percentage']

    def clean(self):
        today = timezone.now().date()

        if self.start_date and self.start_date < today:
            raise ValidationError({"start_date": "start_date debe ser posterior al día actual."})

        if self.end_date and self.end_date <= today:
            raise ValidationError({"end_date": "end_date debe ser posterior al día actual."})

        if self.start_date and self.end_date and self.start_date >= self.end_date:
            raise ValidationError({"end_date": "end_date debe ser mayor a start_date."})

    def __str__(self):
        return f"{self.percentage}% from {self.start_date} to {self.end_date}"


class PieceDiscount(BaseModel):
    piece = models.ForeignKey(Piece, on_delete=models.CASCADE, related_name="discounts")
    discount = models.ForeignKey(Discount, on_delete=models.CASCADE, related_name="piece_discounts")

    class Meta:
        verbose_name = 'Descuento por pieza'
        verbose_name_plural = 'Descuentos por pieza'
        ordering = ['piece']
        constraints = [
            models.UniqueConstraint(
                fields=["piece"],
                condition=models.Q(deleted_at__isnull=True),  
                name="unique_active_piece_discount"
            )
        ]

    def __str__(self):
        return f"{self.piece.title} - {self.discount.percentage}%"


class PiecePhoto(ImagenPKMixin, BaseModel):
    piece = models.ForeignKey(Piece, on_delete=models.CASCADE, related_name="photos")
    image_path = models.ImageField(upload_to=upload_piece_image)
    position = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)]
    )
    
    class Meta:
        verbose_name = 'Foto de la pieza'
        verbose_name_plural = 'Fotos de las piezas'
        unique_together = ('piece', 'position')
        ordering = ['position'] 

    def delete(self, using=None, keep_parents=False, hard=False):
        """PiecePhoto siempre hace hard delete para respetar el unique_together."""
        borrar_archivo_storage(self.image_path)
        super().delete(using=using, keep_parents=keep_parents, hard=True)

    def clean(self):
        if not self.pk:
            count = PiecePhoto.objects.filter(piece=self.piece).count()
            if count >= 10:
                raise ValidationError("Una pieza no puede tener más de 10 fotos.")


    def __str__(self):
        return f"Photo of {self.piece.title}"
