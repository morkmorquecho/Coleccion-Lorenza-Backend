from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from decimal import Decimal
User = get_user_model()
from core.models import BaseModel
from core.utils.validations import validate_date_range
from pieces.models import Piece
from users.models import Address
TRACKING_URLS = {
    'fedex': 'https://www.fedex.com/fedextrack/?trknbr={}',
    'dhl': 'https://www.dhl.com/us-en/home/tracking/tracking-express.html?submit=1&tracking-id={}',
    'ups': 'https://www.ups.com/track?tracknum={}',
}
class Coupon(BaseModel):
    code = models.CharField(max_length=100, unique=True)
    percentage = models.DecimalField(max_digits=5, decimal_places=2)
    valid_from = models.DateField(db_index=True)
    valid_until = models.DateField(db_index=True)
    max_uses = models.PositiveIntegerField(null=True, blank=True)

    def clean(self):
        validate_date_range(self.valid_from, self.valid_until)
        if not (Decimal('0') < self.percentage <= Decimal('100')):
            raise ValidationError({'percentage': 'El porcentaje debe estar entre 0 y 100.'})

    def is_valid(self):
        today = timezone.now().date()
        return self.valid_from <= today <= self.valid_until

    def has_uses_remaining(self):
        if self.max_uses is None:
            return True
        return self.usages.count() < self.max_uses

    def __str__(self):
        return f"{self.code} ({self.percentage}%)"

    class Meta:
        verbose_name = "Cupón"
        verbose_name_plural = "Cupones"
        indexes = [
            models.Index(fields=["valid_from", "valid_until"], name="coupon_validity_idx"),
        ]

class Order(BaseModel):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired')
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    total = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending', db_index=True)
    address = models.ForeignKey(Address, on_delete=models.CASCADE, related_name='orders')

    class Meta:
        indexes = [
            models.Index(fields=["user", "status"], name="order_user_status_idx"),
        ]

    def can_be_cancelled(self) -> bool:
        if self.status == 'cancelled':
            return False

        tracking = self.trakings.first()

        if tracking is None:
            return False

        return tracking.status == 'pending'

    def __str__(self):
        return f"Order #{self.id} - {self.user.username} - {self.status}"


class OrderItem(BaseModel):

    piece = models.ForeignKey(Piece, on_delete=models.CASCADE, related_name='orders_items')
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    quantity = models.IntegerField()
    price_snapshot = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        indexes = [
            models.Index(fields=["order", "piece"], name="orderitem_order_piece_idx"),
        ]

    def __str__(self):
        return f"{self.quantity} x {self.piece} (Order #{self.order.id})"

class ShippingTracking(BaseModel):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    
    CARRIER_CHOICES = [
        ('dhl', 'DHL'),
        ('ups', 'UPS'),
        ('fedex', 'FedEx'),
    ]
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='trakings')
    carrier = models.CharField(max_length=50, choices=CARRIER_CHOICES, default='fedex')
    tracking_number = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending', db_index=True)
    shipped_at = models.DateTimeField (null=True, blank=True, db_index=True) 
    delivered_at = models.DateTimeField (null=True, blank=True)

    class Meta:
        verbose_name = ("Rastreo de pedido")
        verbose_name_plural = ("Rastreo de pedidos") 
        ordering = ['-created_at']


    def get_tracking_url(self):
        if not self.tracking_number:
            return None
        
        url_template = TRACKING_URLS.get(self.carrier.lower())
        if url_template:
            return url_template.format(self.tracking_number)
        return None
    
    def get_owner_id(self):
        return self.order.user_id

    def __str__(self):
        return f"{self.carrier.upper()} - {self.tracking_number} ({self.status})"
    
class Payment(BaseModel):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50)
    external_id = models.CharField(max_length=250, db_index=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending' ,db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["order", "status"], name="payment_order_status_idx"),
        ]   

    def __str__(self):
        return f"Pago {self.id} - {self.order} - {self.status}"

class CouponUsage(BaseModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='coupon_usage')
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name='usages')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='coupon_usage')
    discount_applied = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        indexes = [
            models.Index(fields=["coupon"], name="couponusage_coupon_idx"), 
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "coupon"],
                name="unique_coupon_per_user"
            )
        ]        

    def __str__(self):
        return f"{self.user.username} usó {self.coupon.code} en Order #{self.order.id}"


class ExchangeRate(models.Model):
    usd_to_mxn = models.DecimalField(max_digits=10, decimal_places=4)
    fetched_at = models.DateTimeField(db_index=True) 
    source     = models.CharField(max_length=255)

    class Meta:
        verbose_name = ("Tipo de Cambio")
        verbose_name_plural = ("Tipos de Cambio")

    def __str__(self):
        return f"USD a MXN: {self.usd_to_mxn} ({self.fetched_at.strftime('%d/%m/%Y')})"  