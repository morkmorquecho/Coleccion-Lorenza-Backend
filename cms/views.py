# views.py
from rest_framework import viewsets, mixins
from rest_framework.permissions import AllowAny
from cms.filter import CollectionFilter
from cms.serializers import CollectionDetailSerializer, CollectionListSerializer
from .models import Collection
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Prefetch
from .models import Collection, ImageCollection

class CollectionViewSet(mixins.ListModelMixin,
                        mixins.RetrieveModelMixin,
                        viewsets.GenericViewSet):
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_class = CollectionFilter
    lookup_field='name'

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return CollectionDetailSerializer
        return CollectionListSerializer

    def get_queryset(self):
        if self.action == 'retrieve':
            return Collection.objects.prefetch_related(
                Prefetch('images', queryset=ImageCollection.objects.order_by('-year'))
            ).all()
        return Collection.objects.all()