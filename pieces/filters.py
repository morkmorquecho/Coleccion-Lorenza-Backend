import django_filters
from .models import Piece

class PieceFilter(django_filters.FilterSet):
    featured = django_filters.BooleanFilter()
    section = django_filters.CharFilter(field_name='section__key', lookup_expr='exact')
    type = django_filters.CharFilter(field_name='type__key', lookup_expr='exact')

    class Meta:
        model = Piece
        fields = {
            'featured': ['exact'],
        }