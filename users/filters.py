from django_filters import rest_framework as django_filters
from .models import Address  # o desde donde esté tu modelo

class AddressFilter(django_filters.FilterSet):
    class Meta:
        model = Address
        fields = ['is_default']