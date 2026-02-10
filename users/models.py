from django.db import models
from django.contrib.auth.models import User
from core.models import BaseModel 
from django.core.validators import RegexValidator

phone_regex = RegexValidator(
    regex=r'^\+?1?\d{9,15}$',
    message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
)

class Address(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE) 
    country = models.CharField(max_length=50, choices=[
        ('mexico', 'Mexico'),
        ('usa', 'Estados Unidos'),
        ('canada', 'Canada')])
    state = models.CharField(max_length=100) 
    city = models.CharField(max_length=100)
    street = models.TextField()
    postal_code = models.CharField(max_length=20)
    reference = models.TextField()
    phone_number = models.CharField(validators=[phone_regex], max_length=20)
    street_number = models.IntegerField()
    neighborhood = models.TextField()
    apartment_number = models.CharField(max_length=20, blank=True, null=True)
    is_default = models.BooleanField(default=False)
    recipient_name = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return f"{self.street} {self.street_number}, {self.city}"