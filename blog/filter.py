import django_filters
from .models import Blog


class BlogFilter(django_filters.FilterSet):
    recent = django_filters.BooleanFilter(method='filter_recent')
    status = django_filters.ChoiceFilter(
        choices=[("draft", "Draft"), ("published", "Published")]
    )

    class Meta:
        model = Blog
        fields = ["status"]

    def filter_recent(self, queryset, name, value):
        if value:
            return queryset.order_by('-published_at')[:10]
        return queryset