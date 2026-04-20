from decimal import Decimal
import math
from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.utils import timezone
from auth.adapters import User
from core.models import BaseModel
from core.utils.validations import validate_date_range
from django.apps import apps
from pieces.utils import uplaod_intro_video, upload_piece_image, upload_pieces_thumb, upload_review_image
from django.core.validators import MinValueValidator, MaxValueValidator

from django.core.exceptions import ValidationError

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
    

class Piece( BaseModel):
    thumbnail_path = models.ImageField(upload_to=upload_pieces_thumb)
    intro_video = models.FileField(upload_to=uplaod_intro_video, blank=True, null=True)
    title = models.CharField(max_length=100, unique=True)
    slug = models.CharField(blank=True, null=True, unique=True, max_length=100)
    description = models.TextField()
    
    quantity = models.IntegerField()
    price_base = models.DecimalField(max_digits=10, decimal_places=2, default=0)

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
    
    @property
    def volumetric_weight(self):
        return max((self.width * self.height * self.weight) / 5000, 1)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def get_final_price(self, region: str) -> Decimal:
        peso = math.ceil(self.volumetric_weight)  

        shipping = ShippingRate.objects.filter(
            region=region.upper(),
            kg=peso
        ).first()

        if not shipping:
            return self.price_base

        return self.price_base + shipping.cost
        
    def __str__(self):
        return self.title

class Discount(BaseModel):
    name = models.CharField(max_length=50, default='pendiente de nombrar')
    percentage = models.DecimalField( max_digits=3, decimal_places=1, validators=[MinValueValidator(0.1)])
    start_date = models.DateField()
    end_date = models.DateField()

    class Meta:
        verbose_name = 'Descuento'
        verbose_name_plural = 'Descuentos'
        ordering = ['percentage']

    def clean(self):
        validate_date_range(self.start_date, self.end_date)

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


class PiecePhoto( BaseModel):
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

    def clean(self):
        if not self.pk:
            count = PiecePhoto.objects.filter(piece=self.piece).count()
            if count >= 10:
                raise ValidationError("Una pieza no puede tener más de 10 fotos.")


    def __str__(self):
        return f"Photo of {self.piece.title}"

class ShippingRate(BaseModel):
    region = models.CharField(max_length=10, choices=[('MX', 'México'), ('USA', 'Estados Unidos')])
    kg = models.IntegerField()
    cost = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ['region', 'kg']
        unique_together = ['region', 'kg']  
        verbose_name = 'Tarifa de envío'
        verbose_name_plural = 'Tarifas de envío'

    def __str__(self):
        return f"{self.region} - {self.kg}kg: ${self.cost}"

class Review(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    piece = models.ForeignKey(Piece, on_delete=models.CASCADE)
    comment = models.TextField(blank=True, null=True)
    photo = models.ImageField(upload_to=upload_review_image, blank=True, null=True)
    rating = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5)
        ]
    )
    
    class Meta:
        verbose_name = 'Reseña'
        verbose_name_plural = 'Reseñas'


    def clean(self):
        OrderItem = apps.get_model('orders', 'OrderItem')

        has_purchased = OrderItem.objects.filter(
            order__user=self.user,
            piece=self.piece,
            order__status__in=['paid', 'shipped']
        ).exists()
        
        if not has_purchased:
            raise ValidationError("Solo puedes reseñar piezas que hayas comprado.")
        
    def save(self, *args, **kwargs):
        self.full_clean() 
        super().save(*args, **kwargs)


    def __str__(self):
        return f'reseña de {self.user} a {self.piece.title}'
