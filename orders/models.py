from django.db import models
from django.contrib.auth.models import User
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
    percentage = models.DecimalField(max_digits=3, decimal_places=1)
    valid_from = models.DateField()
    valid_until = models.DateField()

    class Meta:
        verbose_name = ("Cupon")
        verbose_name_plural = ("Cupones")    

    def clean(self):
        validate_date_range(self.valid_from, self.valid_until)

    def __str__(self):
        return f"{self.code} ({self.percentage}%)"

class Order(BaseModel):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('shipped', 'Shipped'),
        ('cancelled', 'Cancelled'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    address = models.ForeignKey(Address, on_delete=models.CASCADE)

    class Meta:
        verbose_name = ("Pedido")
        verbose_name_plural = ("Pedidos")

    def __str__(self):
        return f"Order #{self.id} - {self.user.username} - {self.status}"


class OrderItem(BaseModel):

    piece = models.ForeignKey(Piece, on_delete=models.CASCADE)
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    price_snapshot = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = ("Ítem de Pedido")
        verbose_name_plural = ("Piezas del pedido")

    def __str__(self):
        return f"{self.quantity} x {self.piece} (Order #{self.order.id})"

class ShippingTracking(BaseModel):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_transit', 'In Transit'),
        ('delivered', 'Delivered'),
    ]
    
    CARRIER_CHOICES = [
        ('dhl', 'DHL'),
        ('ups', 'UPS'),
        ('fedex', 'FedEx'),
    ]
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    carrier = models.CharField(max_length=50, choices=CARRIER_CHOICES)
    tracking_number = models.CharField(max_length=100)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    shipped_at = models.DateTimeField (null=True, blank=True)
    delivered_at = models.DateTimeField (null=True, blank=True)

    class Meta:
        verbose_name = ("Rastreo de pedido")
        verbose_name_plural = ("Rastreo de pedidos")   

    def __str__(self):
        return f"{self.carrier.upper()} - {self.tracking_number} ({self.status})"


    def get_tracking_url(self):
        url_template = TRACKING_URLS.get(self.carrier.lower())
        if url_template:
            return url_template.format(self.tracking_number)
        return None
    
class Payment(BaseModel):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50)
    external_id = models.CharField(max_length=250)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')

    class Meta:
        verbose_name = ("Registro de Pago")
        verbose_name_plural = ("Registros de Pagos")   

    def __str__(self):
        return f"Pago {self.id} - {self.order} - {self.status}"

class CouponUsage(BaseModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    discount_applied = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = ("Registro de cupon usado")
        verbose_name_plural = ("Registros de cupones usados")  
        
        constraints = [
            models.UniqueConstraint(
                fields=["user", "coupon"],
                name="unique_coupon_per_user"
            )
        ]        

    def __str__(self):
        return f"{self.user.username} usó {self.coupon.code} en Order #{self.order.id}"
