from decimal import Decimal
import math
from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.utils import timezone
from core.mixins import HEICConversionMixin
from core.models import BaseModel
from core.utils.validations import validate_date_range
from django.apps import apps
from pieces.utils import ceil_to_10, uplaod_intro_video, upload_piece_image, upload_pieces_thumb, upload_review_image
from django.core.validators import MinValueValidator, MaxValueValidator
from decouple import config
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

User = get_user_model()

COMMISSION_STRIPE = Decimal(config('COMMISSION_STRIPE'))
COMISSION_PROCESS_STRIPE = Decimal(config('COMISSION_PROCESS_STRIPE'))



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
    

class Piece(HEICConversionMixin, BaseModel):
    thumbnail_path = models.ImageField(upload_to=upload_pieces_thumb)
    intro_video = models.FileField(upload_to=uplaod_intro_video, blank=True, null=True)
    title = models.CharField(max_length=100, unique=True)
    slug = models.CharField(blank=True, null=True, unique=True, max_length=100)
    description = models.TextField()
    
    quantity = models.PositiveIntegerField()
    price_base = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    width = models.DecimalField(max_digits=10, decimal_places=2)
    height = models.DecimalField(max_digits=10, decimal_places=2)
    length = models.DecimalField(max_digits=10, decimal_places=2)
    weight = models.DecimalField(max_digits=4, decimal_places=2)

    customizable = models.BooleanField(default=False)
    featured = models.BooleanField(default=False)

    type = models.ForeignKey(TypePiece, on_delete=models.CASCADE, related_name="pieces")
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="pieces")
    
    heic_image_fields = ['thumbnail_path']

    class Meta:
        verbose_name = 'Pieza'
        verbose_name_plural = 'Piezas'
    
    def __str__(self):
        return self.title
    
    @property
    def volumetric_weight(self):
        return max((self.width * self.height * self.length) / 5000, 1)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def get_active_discount(self):
        """Fuente de verdad del descuento. Usable desde cualquier capa."""
        if not hasattr(self, '_active_discount_cache'):
            today = timezone.now().date()
            piece_discount = (
                self.discounts
                .filter(
                    deleted_at__isnull=True,
                    discount__start_date__lte=today,
                    discount__end_date__gte=today,
                )
                .select_related('discount')
                .first()
            )
            self._active_discount_cache = piece_discount.discount if piece_discount else None
        return self._active_discount_cache

    def get_final_price(self, region: str, apply_discount: bool = True) -> Decimal:
        peso = max(math.ceil(self.volumetric_weight), self.weight)

        shipping = ShippingRate.objects.filter(
            region=region.upper(), kg=peso
        ).first()

        subtotal = self.price_base + (shipping.cost if shipping else Decimal('0'))

        if apply_discount:
            discount = self.get_active_discount()
            if discount:
                factor = 1 - (Decimal(discount.percentage) / Decimal('100'))
                subtotal = round(subtotal * factor, 2)

        commission_stripe = (subtotal * (COMMISSION_STRIPE / Decimal('100'))) + Decimal('3')
        iva = commission_stripe * Decimal('0.16')

        return Decimal(ceil_to_10(subtotal + commission_stripe + iva))

    def release_stock(self, quantity: int):
        self.quantity += quantity
        self.save(update_fields=['quantity'])

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


class PiecePhoto(HEICConversionMixin, BaseModel):
    piece = models.ForeignKey(Piece, on_delete=models.CASCADE, related_name="photos")
    image_path = models.ImageField(upload_to=upload_piece_image)
    position = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)]
    )
    
    heic_image_fields = ['image_path']

    
    class Meta:
        verbose_name = 'Foto de la pieza'
        verbose_name_plural = 'Fotos de las piezas'
        unique_together = ('piece', 'position')
        ordering = ['position'] 

    def clean(self):
        if not self.pk:
            count = PiecePhoto.objects.filter(piece=self.piece).count()
            if count >= 8:
                raise ValidationError("Una pieza no puede tener más de 10 fotos.")


    def __str__(self):
        return f"Photo of {self.piece.title}"

class ShippingRate(BaseModel):
    region = models.CharField(max_length=10, choices=[('MX', 'México'), ('US', 'Estados Unidos')])
    kg = models.IntegerField()
    cost = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ['region', 'kg']
        unique_together = ['region', 'kg']  
        verbose_name = 'Tarifa de envío'
        verbose_name_plural = 'Tarifas de envío'

    def __str__(self):
        return f"{self.region} - {self.kg}kg: ${self.cost}"

class Review(HEICConversionMixin, BaseModel):
    class ReviewType(models.TextChoices):
        INTERNAL = 'internal', 'Reseña de usuario'
        EXTERNAL = 'external', 'Reseña externa (Etsy, etc.)'

    review_type = models.CharField(
        max_length=10,
        choices=ReviewType.choices,
        default=ReviewType.INTERNAL
    )

    # --- Autor: solo uno de los dos estará presente ---
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        blank=True, null=True,
        related_name='reviews'
    )
    external_author = models.CharField(  # Para reseñas de Etsy
        max_length=150,
        blank=True, null=True
    )

    # --- Resto de campos ---
    piece = models.ForeignKey(Piece, on_delete=models.CASCADE, blank=True, null=True)
    comment = models.TextField(blank=True, null=True)
    link_etsy = models.URLField(max_length=200, blank=True, null=True)
    photo = models.ImageField(upload_to=upload_review_image, blank=True, null=True)
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    created_at = models.DateTimeField(auto_now_add=True)  # recomendado

    heic_image_fields = ['photo']


    class Meta:
        verbose_name = 'Reseña'
        verbose_name_plural = 'Reseñas'
        constraints = [
            # Un usuario solo puede reseñar una pieza una vez
            models.UniqueConstraint(
                fields=['user', 'piece'],
                condition=models.Q(review_type='internal'),
                name='unique_internal_review_per_user_piece'
            )
        ]

    def clean(self):
        if self.review_type == self.ReviewType.INTERNAL:
            self._validate_internal()
        elif self.review_type == self.ReviewType.EXTERNAL:
            self._validate_external()

    def save(self, *args, **kwargs):
        if self.link_etsy and '#reviews' not in self.link_etsy:
            self.link_etsy = self.link_etsy.rstrip('/') + '#reviews'
        super().save(*args, **kwargs)

    def _validate_internal(self):
        if not self.user_id:
            raise ValidationError("Las reseñas internas requieren un usuario.")
        if self.external_author:
            raise ValidationError("Las reseñas internas no deben tener autor externo.")
        if not self.piece_id:
            return
        if self.user.is_staff or self.user.is_superuser:
            return

        OrderItem = apps.get_model('orders', 'OrderItem')
        has_purchased = OrderItem.objects.filter(
            order__user=self.user,
            piece=self.piece,
            order__status__in=['paid', 'shipped']
        ).exists()

        if not has_purchased:
            raise ValidationError("Solo puedes reseñar piezas que hayas comprado.")

    def _validate_external(self):
        if not self.external_author:
            raise ValidationError("Las reseñas externas requieren un nombre de autor.")
        if self.user_id:
            raise ValidationError("Las reseñas externas no deben tener usuario del sistema.")

    @property
    def author_display(self):
        """Nombre a mostrar en el frontend, independiente del tipo."""
        if self.review_type == self.ReviewType.INTERNAL:
            return self.user.get_full_name() or self.user.username
        return self.external_author

    def __str__(self):
        return f'Reseña de {self.author_display} a {self.piece.title if self.piece else "sin pieza"}'