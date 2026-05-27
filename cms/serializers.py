# serializers.py
from rest_framework import serializers

from core.mixins import TranslatedFieldsMixin
from .models import Collection, ImageCollection


class ImageCollectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImageCollection
        fields = ['id', 'image_path', 'year', 'name']


class CollectionListSerializer(TranslatedFieldsMixin, serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()

    class Meta:
        model = Collection
        fields = ['id', 'name', 'description', 'thumbnail_path', 'featured']
    
    def get_name(self, obj):
        return self.get_translated(obj, 'name')

    def get_description(self, obj):
        return self.get_translated(obj, 'description')


class CollectionDetailSerializer(TranslatedFieldsMixin, serializers.ModelSerializer):
    """Con imágenes — para el detalle"""
    images = ImageCollectionSerializer(many=True, read_only=True)

    def get_name(self, obj):
        return self.get_translated(obj, 'name')

    def get_description(self, obj):
        return self.get_translated(obj, 'description')

    class Meta:
        model = Collection
        fields = ['id', 'name', 'description', 'thumbnail_path', 'featured', 'images']