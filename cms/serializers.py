# serializers.py
from rest_framework import serializers
from .models import Collection, ImageCollection


class ImageCollectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImageCollection
        fields = ['id', 'image_path', 'year', 'name']


class CollectionListSerializer(serializers.ModelSerializer):
    """Sin imágenes — para el listado"""
    class Meta:
        model = Collection
        fields = ['id', 'name', 'description', 'thumbnail_path', 'featured']


class CollectionDetailSerializer(serializers.ModelSerializer):
    """Con imágenes — para el detalle"""
    images = ImageCollectionSerializer(many=True, read_only=True)

    class Meta:
        model = Collection
        fields = ['id', 'name', 'description', 'thumbnail_path', 'featured', 'images']