import django_filters
from .models import ShippingTracking

class ShippingTrackingFilter(django_filters.FilterSet):
    date = django_filters.DateFilter(field_name='created_at', lookup_expr='gte')

    class Meta:
        model = ShippingTracking
        fields = {
            'featured': ['exact'],
        }