# filters.py
import django_filters
from .models import Collection


class CollectionFilter(django_filters.FilterSet):
    class Meta:
        model = Collection
        fields = ['featured']