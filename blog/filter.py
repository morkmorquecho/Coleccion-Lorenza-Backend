import django_filters
from .models import Blog


class BlogFilter(django_filters.FilterSet):
    recent = django_filters.BooleanFilter(method='filter_recent')

    class Meta:
        model = Blog
        fields = []

    def filter_recent(self, queryset, name, value):
        if value:
            return queryset.order_by('-created_at')[:10]
        return queryset