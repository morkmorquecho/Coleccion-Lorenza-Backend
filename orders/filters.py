import django_filters
from .models import Order

class OrderFilter(django_filters.FilterSet):
    date = django_filters.DateFilter(field_name='created_at', lookup_expr='gte')

    class Meta:
        model = Order
        fields = {
            'created_at': ['exact'],
        }