import django_filters
from .models import Piece, Review

class PieceFilter(django_filters.FilterSet):
    featured = django_filters.BooleanFilter()
    section = django_filters.CharFilter(field_name='section__key', lookup_expr='exact')
    type = django_filters.CharFilter(field_name='type__key', lookup_expr='exact')

    class Meta:
        model = Piece
        fields = {
            'featured': ['exact'],
        }

class ReviewFilter(django_filters.FilterSet):
    rating_min = django_filters.NumberFilter(field_name='rating', lookup_expr='gte')
    rating_max = django_filters.NumberFilter(field_name='rating', lookup_expr='lte')

    class Meta:
        model = Review
        fields = ['user', 'piece', 'rating', 'rating_min', 'rating_max']
